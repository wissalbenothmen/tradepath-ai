from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.trade_document import TradeDocument, DocumentType
from app.models.shipment import Shipment
from app.models.user import User
from app.services.document_ocr import extract_commercial_invoice
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/documents", tags=["documents"])


class DocumentOut(BaseModel):
    id: uuid.UUID
    shipment_id: uuid.UUID
    document_type: DocumentType
    filename: str
    ocr_extracted: Optional[dict]
    ocr_confidence: Optional[float]
    processing_status: str

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    shipment_id: uuid.UUID = Form(...),
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ship_result = await db.execute(
        select(Shipment).where(Shipment.id == shipment_id, Shipment.company_id == current_user.company_id)
    )
    if not ship_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")

    file_bytes = await file.read()

    doc = TradeDocument(
        company_id=current_user.company_id,
        shipment_id=shipment_id,
        uploaded_by=current_user.id,
        document_type=document_type,
        filename=file.filename or "upload",
        processing_status="processing",
    )
    db.add(doc)
    await db.flush()

    if document_type == DocumentType.COMMERCIAL_INVOICE:
        extracted = await extract_commercial_invoice(file_bytes, file.filename or "upload")
        doc.ocr_extracted = extracted
        doc.ocr_confidence = extracted.get("confidence")
        doc.processing_status = "completed" if not extracted.get("error") else "failed"
    else:
        doc.processing_status = "completed"

    await log_action(db, "document_uploaded", "trade_document", str(doc.id),
                     current_user.id, shipment_id, {"document_type": document_type.value})
    return doc


@router.get("/shipment/{shipment_id}", response_model=list[DocumentOut])
async def list_documents(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sh_check = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    )
    if not sh_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")
    result = await db.execute(
        select(TradeDocument)
        .where(
            TradeDocument.shipment_id == shipment_id,
            TradeDocument.company_id == current_user.company_id,
        )
        .order_by(TradeDocument.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(TradeDocument).where(
            TradeDocument.id == document_id,
            TradeDocument.company_id == current_user.company_id,
        )
    )
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc
