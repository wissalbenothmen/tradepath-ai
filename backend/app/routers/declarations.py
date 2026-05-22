from __future__ import annotations
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.customs_declaration import CustomsDeclaration, DeclarationType, DeclarationStatus
from app.models.shipment import Shipment
from app.models.user import User
from app.services.customs_declaration_service import (
    generate_edi_x12_309, generate_edifact_cusdec, validate_declaration
)
from app.services.duty_calculator import calculate_duties
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/declarations", tags=["declarations"])


class DeclarationCreate(BaseModel):
    shipment_id: uuid.UUID
    declaration_type: DeclarationType
    port_of_entry: Optional[str] = None
    declared_value_usd: Optional[float] = None
    cif_value_usd: Optional[float] = None
    fob_value_usd: Optional[float] = None
    declaration_data: Optional[dict] = None


class DeclarationOut(BaseModel):
    id: uuid.UUID
    shipment_id: uuid.UUID
    declaration_type: DeclarationType
    status: DeclarationStatus
    entry_number: Optional[str]
    port_of_entry: Optional[str]
    declared_value_usd: Optional[float]
    cif_value_usd: Optional[float]
    fob_value_usd: Optional[float]
    total_duty_usd: Optional[float]
    total_tax_usd: Optional[float]
    inconsistencies: Optional[list]
    gpt_validation_notes: Optional[str]
    edi_content: Optional[str]

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=DeclarationOut, status_code=201)
async def create_declaration(
    body: DeclarationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ship_result = await db.execute(
        select(Shipment).where(Shipment.id == body.shipment_id, Shipment.company_id == current_user.company_id)
    )
    shipment = ship_result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    declaration = CustomsDeclaration(
        company_id=current_user.company_id,
        shipment_id=body.shipment_id,
        created_by=current_user.id,
        declaration_type=body.declaration_type,
        port_of_entry=body.port_of_entry,
        declared_value_usd=body.declared_value_usd,
        cif_value_usd=body.cif_value_usd,
        fob_value_usd=body.fob_value_usd,
        declaration_data=body.declaration_data,
    )

    # Calculate duties if values provided
    if body.cif_value_usd and body.fob_value_usd:
        duty_result = calculate_duties(
            cif_value_usd=body.cif_value_usd,
            fob_value_usd=body.fob_value_usd,
            duty_rate=0.05,
            destination_country=shipment.destination_country,
            hs_code_6digit="000000",
            origin_country=shipment.origin_country,
        )
        declaration.total_duty_usd = duty_result["total_duty_usd"]
        declaration.total_tax_usd = duty_result["total_tax_usd"]

    db.add(declaration)
    await db.flush()
    await log_action(db, "declaration_created", "customs_declaration", str(declaration.id),
                     current_user.id, body.shipment_id)
    return declaration


@router.post("/{declaration_id}/validate", response_model=DeclarationOut)
async def validate_declaration_route(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomsDeclaration).where(
            CustomsDeclaration.id == declaration_id,
            CustomsDeclaration.company_id == current_user.company_id,
        )
    )
    declaration = result.scalar_one_or_none()
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")

    validation = await validate_declaration(
        declaration_data=declaration.declaration_data or {},
        line_items=[],
        declaration_type=declaration.declaration_type.value,
    )
    declaration.inconsistencies = validation.get("inconsistencies", [])
    declaration.gpt_validation_notes = validation.get("gpt_validation_notes")
    declaration.status = DeclarationStatus.REVIEW
    await db.flush()
    return declaration


@router.post("/{declaration_id}/generate-edi", response_model=DeclarationOut)
async def generate_edi(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomsDeclaration).where(
            CustomsDeclaration.id == declaration_id,
            CustomsDeclaration.company_id == current_user.company_id,
        )
    )
    declaration = result.scalar_one_or_none()
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")

    ship_result = await db.execute(
        select(Shipment).where(
            Shipment.id == declaration.shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    )
    shipment = ship_result.scalar_one_or_none()

    data = {
        "shipment": {
            "reference_number": shipment.reference_number if shipment else "",
            "origin_country": shipment.origin_country if shipment else "",
            "destination_country": shipment.destination_country if shipment else "",
            "exporter_name": shipment.exporter_name if shipment else "",
            "consignee_name": shipment.consignee_name if shipment else "",
            "currency": shipment.currency if shipment else "USD",
        },
        "declared_value_usd": declaration.declared_value_usd,
    }

    if declaration.declaration_type in (DeclarationType.CBP_ENTRY_01, DeclarationType.AES_FILING):
        declaration.edi_content = generate_edi_x12_309(data)
    else:
        declaration.edi_content = generate_edifact_cusdec(data)

    await db.flush()
    return declaration


@router.post("/{declaration_id}/submit", response_model=DeclarationOut)
async def submit_declaration(
    declaration_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(CustomsDeclaration).where(
            CustomsDeclaration.id == declaration_id,
            CustomsDeclaration.company_id == current_user.company_id,
        )
    )
    declaration = result.scalar_one_or_none()
    if not declaration:
        raise HTTPException(status_code=404, detail="Declaration not found")
    declaration.status = DeclarationStatus.SUBMITTED
    declaration.submitted_at = datetime.now(timezone.utc)
    await db.flush()
    await log_action(db, "declaration_submitted", "customs_declaration", str(declaration_id),
                     current_user.id, declaration.shipment_id)
    return declaration


@router.get("/shipment/{shipment_id}", response_model=list[DeclarationOut])
async def list_declarations(
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
        select(CustomsDeclaration)
        .where(
            CustomsDeclaration.shipment_id == shipment_id,
            CustomsDeclaration.company_id == current_user.company_id,
        )
        .order_by(CustomsDeclaration.created_at.desc())
    )
    return result.scalars().all()
