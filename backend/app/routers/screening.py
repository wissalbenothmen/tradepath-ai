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
from app.models.denied_party_screening import DeniedPartyScreening, ScreeningResult
from app.models.shipment import Shipment
from app.models.user import User
from app.services.denied_party_screening import screen_party
from app.services.audit_log_service import log_action

router = APIRouter(prefix="/screening", tags=["screening"])


class ScreenRequest(BaseModel):
    shipment_id: uuid.UUID
    party_name: str
    party_type: str  # consignee/shipper/notify/manufacturer
    party_country: Optional[str] = None
    lists_to_check: Optional[list[str]] = None


class ReviewRequest(BaseModel):
    decision: str  # approved/rejected/escalated
    notes: Optional[str] = None
    apply_legal_hold: bool = False
    whitelist: bool = False


class ScreeningOut(BaseModel):
    id: uuid.UUID
    shipment_id: uuid.UUID
    party_name: str
    party_type: str
    party_country: Optional[str]
    overall_result: ScreeningResult
    highest_score: float
    matches: Optional[list]
    lists_checked: Optional[list]
    legal_hold_applied: str
    whitelisted: str

    model_config = ConfigDict(from_attributes=True)
@router.post("", response_model=ScreeningOut, status_code=201)
async def screen_shipment_party(
    body: ScreenRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify shipment access — keep the object for later status update
    ship_result = await db.execute(
        select(Shipment).where(Shipment.id == body.shipment_id, Shipment.company_id == current_user.company_id)
    )
    ship = ship_result.scalar_one_or_none()
    if not ship:
        raise HTTPException(status_code=404, detail="Shipment not found")

    result = await screen_party(body.party_name, body.party_country, body.lists_to_check)

    screening = DeniedPartyScreening(
        company_id=current_user.company_id,
        shipment_id=body.shipment_id,
        screened_by=current_user.id,
        party_name=body.party_name,
        party_type=body.party_type,
        party_country=body.party_country,
        overall_result=ScreeningResult(result["overall_result"]),
        matches=result["matches"],
        lists_checked=result["lists_checked"],
        highest_score=result["highest_score"],
    )
    db.add(screening)
    await db.flush()

    # Update shipment denied_party_status
    if ship:
        # Keep worst status
        status_priority = {"positive_match": 2, "potential_match": 1, "clear": 0}
        current_priority = status_priority.get(ship.denied_party_status or "clear", 0)
        new_priority = status_priority.get(result["overall_result"], 0)
        if new_priority > current_priority:
            ship.denied_party_status = result["overall_result"]

    await log_action(db, "party_screened", "denied_party_screening", str(screening.id),
                     current_user.id, body.shipment_id,
                     {"party_name": body.party_name, "result": result["overall_result"]})
    return screening


@router.post("/{screening_id}/review", response_model=ScreeningOut)
async def review_screening(
    screening_id: uuid.UUID,
    body: ReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(DeniedPartyScreening).where(
            DeniedPartyScreening.id == screening_id,
            DeniedPartyScreening.company_id == current_user.company_id,
        )
    )
    screening = result.scalar_one_or_none()
    if not screening:
        raise HTTPException(status_code=404, detail="Screening not found")
    screening.reviewed_by = current_user.id
    screening.review_decision = body.decision
    screening.review_notes = body.notes
    screening.legal_hold_applied = "true" if body.apply_legal_hold else "false"
    if body.whitelist:
        from datetime import datetime, timezone, timedelta
        screening.whitelisted = "true"
        screening.whitelist_expiry = datetime.now(timezone.utc) + timedelta(days=365)
    await db.flush()
    return screening


@router.get("/shipment/{shipment_id}", response_model=list[ScreeningOut])
async def list_shipment_screenings(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Confirm the caller owns the shipment first (avoids cross-tenant existence
    # probing via shipment_id enumeration).
    sh_check = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    )
    if not sh_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")

    result = await db.execute(
        select(DeniedPartyScreening).where(
            DeniedPartyScreening.shipment_id == shipment_id,
            DeniedPartyScreening.company_id == current_user.company_id,
        )
        .order_by(DeniedPartyScreening.screened_at.desc())
    )
    return result.scalars().all()
