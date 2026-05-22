from __future__ import annotations
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.audit_log import AuditLog


async def log_action(
    db: AsyncSession,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    user_id: uuid.UUID | None = None,
    shipment_id: uuid.UUID | None = None,
    details: dict[str, Any] | None = None,
    ai_reasoning: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        user_id=user_id,
        shipment_id=shipment_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ai_reasoning=ai_reasoning,
    )
    db.add(entry)
    await db.flush()
    return entry
