"""Tenant-isolation helpers.

Every authenticated request belongs to exactly one tenant (``company_id``).
These helpers enforce that *no* row outside the caller's tenant can be read
or mutated by request handlers. They are deliberately tiny so they read as
obviously-correct in PRs.

Design notes:
- We use the ``company_id`` column we added to every domain table (HSClassification,
  DeniedPartyScreening, CustomsDeclaration, CertificateOfOrigin, FTAAnalysis,
  TradeDocument). Older rows where ``company_id IS NULL`` are deliberately
  excluded — the safe default is "deny".
- For ``Shipment``, ``company_id`` is non-nullable from the start.
- ``require_shipment(...)`` is the single place that translates a user-supplied
  shipment UUID into a Shipment object, after verifying the caller owns it.
"""
from __future__ import annotations

import uuid
from typing import Type, TypeVar

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import Shipment
from app.models.user import User

T = TypeVar("T")


async def require_shipment(
    db: AsyncSession, shipment_id: uuid.UUID, user: User
) -> Shipment:
    """Return the Shipment iff it belongs to the caller's tenant, else 404.

    404 (not 403) is intentional: we don't leak existence of cross-tenant rows.
    """
    result = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.company_id == user.company_id,
        )
    )
    shipment = result.scalar_one_or_none()
    if not shipment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


async def require_tenant_owned(
    db: AsyncSession, model: Type[T], obj_id: uuid.UUID, user: User
) -> T:
    """Generic helper: load ``model[obj_id]`` only if ``company_id == user.company_id``.

    Used by classification/screening/declaration/coo/fta/document GET endpoints.
    """
    result = await db.execute(
        select(model).where(
            model.id == obj_id,  # type: ignore[attr-defined]
            model.company_id == user.company_id,  # type: ignore[attr-defined]
        )
    )
    obj = result.scalar_one_or_none()
    if not obj:
        # Generic name preserves info-leak protection.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")
    return obj
