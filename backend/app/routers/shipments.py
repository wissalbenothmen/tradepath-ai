from __future__ import annotations
import uuid
from datetime import date
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.shipment import Shipment, ShipmentStatus, TransportMode
from app.models.shipment_amendment import ShipmentAmendment
from app.models.shipment_line_item import ShipmentLineItem
from app.models.trade_document import TradeDocument
from app.models.user import User
from app.services.audit_log_service import log_action
from app.services.trade_amendment_analyzer import TradeAmendmentAnalyzer
from app.services.amendment_brief_pdf_service import (
    render_amendment_brief_pdf,
    safe_pdf_filename,
)

router = APIRouter(prefix="/shipments", tags=["shipments"])


class ShipmentCreate(BaseModel):
    origin_country: str
    destination_country: str
    transport_mode: Optional[TransportMode] = None
    incoterms: Optional[str] = None
    exporter_name: Optional[str] = None
    importer_name: Optional[str] = None
    consignee_name: Optional[str] = None
    notify_party: Optional[str] = None
    manufacturer_name: Optional[str] = None
    freight_forwarder: Optional[str] = None
    total_value_usd: Optional[float] = None
    total_weight_kg: Optional[float] = None
    currency: str = "USD"
    shipment_date: Optional[date] = None
    notes: Optional[str] = None


class ShipmentOut(BaseModel):
    id: uuid.UUID
    reference_number: str
    company_id: uuid.UUID
    created_by: uuid.UUID
    status: ShipmentStatus
    transport_mode: Optional[TransportMode]
    origin_country: str
    destination_country: str
    incoterms: Optional[str]
    exporter_name: Optional[str]
    importer_name: Optional[str]
    consignee_name: Optional[str]
    total_value_usd: Optional[float]
    denied_party_status: Optional[str]
    restriction_status: Optional[str]

    model_config = ConfigDict(from_attributes=True)
def _generate_ref(company_id: uuid.UUID) -> str:
    short = str(company_id).replace("-", "")[:6].upper()
    import random, string
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"TP-{short}-{suffix}"


@router.post("", response_model=ShipmentOut, status_code=201)
async def create_shipment(
    body: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    shipment = Shipment(
        reference_number=_generate_ref(current_user.company_id),
        company_id=current_user.company_id,
        created_by=current_user.id,
        **body.model_dump(exclude_none=True),
    )
    db.add(shipment)
    await db.flush()
    await log_action(db, "shipment_created", "shipment", str(shipment.id), current_user.id, shipment.id)
    return shipment


@router.get("", response_model=list[ShipmentOut])
async def list_shipments(
    status: Optional[ShipmentStatus] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = select(Shipment).where(Shipment.company_id == current_user.company_id)
    if status:
        q = q.where(Shipment.status == status)
    q = q.order_by(Shipment.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{shipment_id}", response_model=ShipmentOut)
async def get_shipment(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id, Shipment.company_id == current_user.company_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    return shipment


@router.patch("/{shipment_id}/status", response_model=ShipmentOut)
async def update_status(
    shipment_id: uuid.UUID,
    new_status: ShipmentStatus,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id, Shipment.company_id == current_user.company_id)
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    shipment.status = new_status
    await db.flush()
    await log_action(db, "status_updated", "shipment", str(shipment_id), current_user.id, shipment_id,
                     {"new_status": new_status.value})
    return shipment


# ===== Phase B + C — voice amendment ↔ trade-document cross-validation + brief PDF =====

async def _gather_amendment(shipment_id: uuid.UUID, company_id: uuid.UUID, db: AsyncSession):
    sh_q = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id, Shipment.company_id == company_id,
        )
    )
    shipment = sh_q.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    am_q = await db.execute(
        select(ShipmentAmendment)
        .where(ShipmentAmendment.shipment_id == shipment_id)
        .order_by(ShipmentAmendment.created_at.desc())
    )
    latest = am_q.scalars().first()
    transcript = (latest.voice_transcript if latest else "") or ""

    li_q = await db.execute(
        select(ShipmentLineItem).where(ShipmentLineItem.shipment_id == shipment_id)
    )
    line_items = li_q.scalars().all()
    line_item_dicts = [
        {
            "id": str(li.id),
            "line_number": li.line_number,
            "product_description": li.product_description,
            "hs_code": li.hs_code,
            "country_of_origin": li.country_of_origin,
            "quantity": li.quantity,
            "unit": li.unit,
            "unit_value_usd": li.unit_value_usd,
            "total_value_usd": li.total_value_usd,
            "weight_kg": li.weight_kg,
        }
        for li in line_items
    ]

    doc_q = await db.execute(
        select(TradeDocument).where(TradeDocument.shipment_id == shipment_id)
    )
    documents = doc_q.scalars().all()
    document_dicts = [
        {
            "id": str(d.id),
            "document_type": d.document_type.value if hasattr(d.document_type, "value") else str(d.document_type),
            "filename": d.filename,
            "ocr_extracted": d.ocr_extracted,
            "ocr_confidence": d.ocr_confidence,
        }
        for d in documents
    ]

    analyzer = TradeAmendmentAnalyzer()
    result = await analyzer.analyze(transcript, line_item_dicts, document_dicts)
    return shipment, transcript, line_item_dicts, document_dicts, result


@router.post("/{shipment_id}/amendment-cross-validate")
async def amendment_cross_validate(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phase B — cross-check the latest voice amendment against line items + trade documents."""
    shipment, transcript, line_items, documents, result = await _gather_amendment(
        shipment_id, current_user.company_id, db,
    )
    return {
        "status": "completed" if transcript else "no_transcript",
        "mode": result.get("mode"),
        "shipment_id": str(shipment_id),
        "transcript_excerpt": transcript[:500],
        "line_items_checked": len(line_items),
        "documents_checked": len(documents),
        "voice_claims": result.get("voice_claims", {}),
        "document_state": result.get("document_state", {}),
        "contradictions": result.get("contradictions", []),
        "missing_evidence": result.get("missing_evidence", []),
        "talking_points": result.get("talking_points", []),
        "narrative": result.get("narrative"),
    }


@router.get("/{shipment_id}/voice-records")
async def list_shipment_voice_records(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phase E — list persisted voice amendment transcripts for this shipment."""
    sh_q = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id, Shipment.company_id == current_user.company_id,
        )
    )
    if not sh_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")

    am_q = await db.execute(
        select(ShipmentAmendment)
        .where(ShipmentAmendment.shipment_id == shipment_id)
        .order_by(ShipmentAmendment.created_at.desc())
    )
    records = am_q.scalars().all()
    return [
        {
            "id": str(a.id),
            "voice_transcript": a.voice_transcript,
            "transcript_status": a.transcript_status,
            "provider": a.provider,
            "created_at": a.created_at.isoformat() if a.created_at else None,
        }
        for a in records
    ]


@router.get("/{shipment_id}/amendment-brief.pdf")
async def amendment_brief_pdf(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Phase C — render the customs amendment brief PDF."""
    shipment, transcript, line_items, documents, result = await _gather_amendment(
        shipment_id, current_user.company_id, db,
    )
    pdf_bytes = render_amendment_brief_pdf(
        shipment={
            "reference_number": shipment.reference_number,
            "origin_country": shipment.origin_country,
            "destination_country": shipment.destination_country,
            "exporter_name": shipment.exporter_name,
            "importer_name": shipment.importer_name,
            "status": shipment.status.value if hasattr(shipment.status, "value") else str(shipment.status),
        },
        transcript=transcript or None,
        voice_claims=result.get("voice_claims", {}),
        document_state=result.get("document_state", {}),
        contradictions=result.get("contradictions", []),
        missing_evidence=result.get("missing_evidence", []),
        talking_points=result.get("talking_points", []),
        narrative=result.get("narrative"),
        generated_by=getattr(current_user, "email", None) or str(current_user.id),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{safe_pdf_filename(shipment.reference_number)}"',
            "X-TradePath-Contradictions": str(len(result.get("contradictions", []))),
            "X-TradePath-Missing": str(len(result.get("missing_evidence", []))),
            "X-TradePath-Mode": result.get("mode", "unknown"),
        },
    )
