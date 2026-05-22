from __future__ import annotations
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.auth import get_current_user
from app.models.user import User
from app.services.import_restrictions import check_import_restrictions

router = APIRouter(prefix="/restrictions", tags=["restrictions"])


class RestrictionRequest(BaseModel):
    origin_country: str
    destination_country: str
    hs_code_6digit: str
    is_itar_ear: bool = False


class RestrictionResult(BaseModel):
    status: str
    reasons: list[str]


@router.post("/check", response_model=RestrictionResult)
async def check_restrictions(
    body: RestrictionRequest,
    current_user: User = Depends(get_current_user),
):
    result = check_import_restrictions(
        origin_country=body.origin_country,
        destination_country=body.destination_country,
        hs_code_6digit=body.hs_code_6digit,
        is_itar_ear=body.is_itar_ear,
    )
    return result
