from __future__ import annotations
from datetime import timezone
import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth import get_current_user
from app.database import get_db
from app.models.hs_classification import HSClassification, ClassificationStatus
from app.models.user import User
from app.services.hs_classifier import classify_hs_code
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/classification", tags=["classification"])


class ClassifyRequest(BaseModel):
    product_description: str
    materials: Optional[str] = None
    intended_use: Optional[str] = None
    country_of_origin: Optional[str] = None
    product_id: Optional[uuid.UUID] = None
    line_item_id: Optional[uuid.UUID] = None


class ClassificationOut(BaseModel):
    id: uuid.UUID
    status: ClassificationStatus
    hs_code_6digit: str
    hs_code_us_hts: Optional[str]
    hs_code_eu_taric: Optional[str]
    hs_code_uk_gt: Optional[str]
    confidence: float
    gri_rules_applied: Optional[list]
    top_candidates: Optional[list]
    gpt_reasoning: Optional[str]
    duty_rate_us: Optional[float]
    duty_rate_eu: Optional[float]
    anti_dumping_duty: Optional[float]
    is_itar_ear_flagged: str

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=ClassificationOut, status_code=201)
async def classify_product(
    body: ClassifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await classify_hs_code(
        product_description=body.product_description,
        materials=body.materials,
        intended_use=body.intended_use,
        country_of_origin=body.country_of_origin,
    )

    classification = HSClassification(
        company_id=current_user.company_id,
        product_id=body.product_id,
        line_item_id=body.line_item_id,
        classified_by=current_user.id,
        status=ClassificationStatus.CLASSIFIED,
        hs_code_6digit=result["hs_code_6digit"],
        hs_code_us_hts=result.get("hs_code_us_hts"),
        hs_code_eu_taric=result.get("hs_code_eu_taric"),
        hs_code_uk_gt=result.get("hs_code_uk_gt"),
        confidence=result.get("confidence", 0.0),
        gri_rules_applied=result.get("gri_rules_applied"),
        top_candidates=result.get("top_candidates"),
        gpt_reasoning=result.get("gpt_reasoning"),
        duty_rate_us=result.get("duty_rate_us"),
        duty_rate_eu=result.get("duty_rate_eu"),
        anti_dumping_duty=result.get("anti_dumping_duty"),
        is_itar_ear_flagged=result.get("is_itar_ear_flagged", "false"),
    )
    db.add(classification)
    await db.flush()
    await log_action(db, "hs_classified", "hs_classification", str(classification.id),
                     current_user.id, ai_reasoning=result.get("gpt_reasoning"))
    return classification


@router.post("/{classification_id}/confirm", response_model=ClassificationOut)
async def confirm_classification(
    classification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from datetime import datetime, timezone
    result = await db.execute(
        select(HSClassification).where(
            HSClassification.id == classification_id,
            HSClassification.company_id == current_user.company_id,
        )
    )
    classification = result.scalar_one_or_none()
    if not classification:
        raise HTTPException(status_code=404, detail="Classification not found")
    classification.status = ClassificationStatus.CONFIRMED
    classification.confirmed_by = current_user.id
    classification.confirmed_at = datetime.now(timezone.utc)
    await db.flush()
    return classification


@router.get("", response_model=list[ClassificationOut])
async def list_classifications(
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List the caller's classifications (most recent first)."""
    limit = max(1, min(limit, 200))
    result = await db.execute(
        select(HSClassification)
        .where(HSClassification.company_id == current_user.company_id)
        .order_by(HSClassification.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/{classification_id}", response_model=ClassificationOut)
async def get_classification(
    classification_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(HSClassification).where(
            HSClassification.id == classification_id,
            HSClassification.company_id == current_user.company_id,
        )
    )
    c = result.scalar_one_or_none()
    if not c:
        raise HTTPException(status_code=404, detail="Classification not found")
    return c
