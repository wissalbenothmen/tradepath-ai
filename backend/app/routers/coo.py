from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.certificate_of_origin import CertificateOfOrigin, COOFormat, OriginCriterion
from app.models.shipment import Shipment
from app.models.user import User
from app.services.coo_generator import analyze_origin_and_generate_coo, calculate_rvc
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/coo", tags=["coo"])


class COOCreate(BaseModel):
    shipment_id: uuid.UUID
    coo_format: COOFormat
    fta_agreement: Optional[str] = None
    exporter_name: str
    producer_name: Optional[str] = None
    importer_name: str
    country_of_origin: str
    transaction_value_usd: Optional[float] = None
    non_originating_materials_usd: Optional[float] = None


class COOOut(BaseModel):
    id: uuid.UUID
    shipment_id: uuid.UUID
    coo_format: COOFormat
    origin_criterion: OriginCriterion
    fta_agreement: Optional[str]
    exporter_name: str
    importer_name: str
    country_of_origin: str
    origin_analysis: Optional[str]
    rvc_percentage: Optional[float]
    preferential_duty_saving_usd: Optional[float]
    document_content: Optional[str]
    is_certified: str

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=COOOut, status_code=201)
async def create_coo(
    body: COOCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ship_result = await db.execute(
        select(Shipment).where(Shipment.id == body.shipment_id, Shipment.company_id == current_user.company_id)
    )
    shipment = ship_result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    # Calculate RVC if values provided
    rvc_data = None
    rvc_pct = None
    if body.transaction_value_usd and body.non_originating_materials_usd is not None:
        rvc_data = calculate_rvc(
            body.transaction_value_usd,
            body.non_originating_materials_usd,
            body.fta_agreement or "DEFAULT",
        )
        rvc_pct = rvc_data["rvc_percentage"]

    analysis = await analyze_origin_and_generate_coo(
        shipment_data={
            "reference_number": shipment.reference_number,
            "origin_country": shipment.origin_country,
            "destination_country": shipment.destination_country,
            "total_value_usd": shipment.total_value_usd,
            "exporter_name": body.exporter_name,
            "importer_name": body.importer_name,
            "fta_agreement": body.fta_agreement,
            "transaction_value_usd": body.transaction_value_usd,
            "non_originating_materials_usd": body.non_originating_materials_usd,
        },
        line_items=[],
        coo_format=body.coo_format.value,
    )

    criterion_str = analysis.get("origin_criterion", "substantial_transformation")
    try:
        criterion = OriginCriterion(criterion_str)
    except ValueError:
        criterion = OriginCriterion.SUBSTANTIAL_TRANSFORMATION

    coo = CertificateOfOrigin(
        company_id=current_user.company_id,
        shipment_id=body.shipment_id,
        created_by=current_user.id,
        coo_format=body.coo_format,
        origin_criterion=criterion,
        fta_agreement=body.fta_agreement,
        exporter_name=body.exporter_name,
        producer_name=body.producer_name,
        importer_name=body.importer_name,
        country_of_origin=body.country_of_origin,
        origin_analysis=analysis.get("origin_analysis"),
        rvc_percentage=rvc_pct or analysis.get("rvc_percentage"),
        rvc_calculation=rvc_data,
        preferential_duty_saving_usd=analysis.get("preferential_duty_saving_usd"),
        document_content=analysis.get("document_content"),
    )
    db.add(coo)
    await db.flush()
    await log_action(db, "coo_generated", "certificate_of_origin", str(coo.id),
                     current_user.id, body.shipment_id, ai_reasoning=analysis.get("origin_analysis"))
    return coo


@router.get("/shipment/{shipment_id}", response_model=list[COOOut])
async def list_coos(
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
        select(CertificateOfOrigin)
        .where(
            CertificateOfOrigin.shipment_id == shipment_id,
            CertificateOfOrigin.company_id == current_user.company_id,
        )
        .order_by(CertificateOfOrigin.created_at.desc())
    )
    return result.scalars().all()
