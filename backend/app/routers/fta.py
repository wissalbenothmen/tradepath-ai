from __future__ import annotations
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.fta_analysis import FTAAnalysis
from app.models.shipment import Shipment
from app.models.user import User
from app.services.fta_analyzer import analyze_fta
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/fta", tags=["fta"])


class FTAAnalyzeRequest(BaseModel):
    shipment_id: uuid.UUID
    hs_code_6digit: str
    product_description: str
    declared_value_usd: float


class FTAOut(BaseModel):
    id: uuid.UUID
    shipment_id: uuid.UUID
    hs_code: str
    applicable_ftas: Optional[list]
    mfn_duty_rate: Optional[float]
    preferential_duty_rate: Optional[float]
    duty_saving_usd: Optional[float]
    gpt_analysis: Optional[str]

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=FTAOut, status_code=201)
async def run_fta_analysis(
    body: FTAAnalyzeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ship_result = await db.execute(
        select(Shipment).where(Shipment.id == body.shipment_id, Shipment.company_id == current_user.company_id)
    )
    shipment = ship_result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")

    result = await analyze_fta(
        origin_country=shipment.origin_country,
        destination_country=shipment.destination_country,
        hs_code_6digit=body.hs_code_6digit,
        declared_value_usd=body.declared_value_usd,
        product_description=body.product_description,
    )

    fta = FTAAnalysis(
        company_id=current_user.company_id,
        shipment_id=body.shipment_id,
        origin_country=shipment.origin_country,
        destination_country=shipment.destination_country,
        hs_code=body.hs_code_6digit,
        applicable_ftas=result.get("applicable_ftas", []),
        mfn_duty_rate=result.get("mfn_duty_rate"),
        preferential_duty_rate=result.get("preferential_duty_rate"),
        duty_saving_usd=result.get("duty_saving_usd"),
        gpt_analysis=result.get("gpt_analysis"),
    )
    db.add(fta)
    await db.flush()
    await log_action(db, "fta_analyzed", "fta_analysis", str(fta.id),
                     current_user.id, body.shipment_id, ai_reasoning=result.get("gpt_analysis"))
    return fta


@router.get("/shipment/{shipment_id}", response_model=list[FTAOut])
async def list_fta_analyses(
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
        select(FTAAnalysis)
        .where(
            FTAAnalysis.shipment_id == shipment_id,
            FTAAnalysis.company_id == current_user.company_id,
        )
        .order_by(FTAAnalysis.created_at.desc())
    )
    return result.scalars().all()
