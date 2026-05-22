"""Shipment-amendment voice router — Phase A from the audit-pipeline recipe.

POST /api/v1/shipment-amendments/shipment/{shipment_id}/upload  — audio → Whisper → ShipmentAmendment
GET  /api/v1/shipment-amendments/shipment/{shipment_id}         — list verbal amendments
"""
from __future__ import annotations

import os
import tempfile
import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_user
from app.database import get_db
from app.models.user import User
from app.models.shipment import Shipment
from app.models.shipment_amendment import ShipmentAmendment
from app.services.whisper_service import WhisperService

router = APIRouter(prefix="/shipment-amendments", tags=["shipment-amendments"])

_ALLOWED_AUDIO_EXT = {".wav", ".mp3", ".m4a", ".mp4", ".webm", ".ogg", ".flac"}


def _validate_audio_filename(filename: str) -> str:
    if not filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    ext = os.path.splitext(filename)[1].lower()
    if ext not in _ALLOWED_AUDIO_EXT:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type {ext!r}. Allowed: {sorted(_ALLOWED_AUDIO_EXT)}",
        )
    return ext


def _serialize(a: ShipmentAmendment) -> Dict[str, Any]:
    return {
        "id": str(a.id),
        "shipment_id": str(a.shipment_id),
        "agent_id": str(a.agent_id) if a.agent_id else None,
        "amendment_type": a.amendment_type,
        "voice_file_url": a.voice_file_url,
        "voice_transcript": a.voice_transcript,
        "transcript_status": a.transcript_status,
        "target_field": a.target_field,
        "previous_value": a.previous_value,
        "new_value": a.new_value,
        "status": a.status,
        "provider": a.provider,
        "model": a.model,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }


@router.post("/shipment/{shipment_id}/upload", status_code=status.HTTP_201_CREATED)
async def upload_amendment(
    shipment_id: uuid.UUID,
    file: UploadFile = File(...),
    amendment_type: str = Form("correction"),
    target_field: Optional[str] = Form(None),
    previous_value: Optional[str] = Form(None),
    new_value: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Audio file → Whisper transcript → ShipmentAmendment row."""
    sh_q = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    )
    if not sh_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")

    ext = _validate_audio_filename(file.filename or "")
    content_bytes = await file.read()
    if not content_bytes:
        raise HTTPException(status_code=400, detail="Empty audio file")

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(content_bytes)
        tmp_path = tmp.name

    try:
        whisper = WhisperService()
        result = await whisper.transcribe_audio(tmp_path)
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass

    if "error" in result:
        raise HTTPException(status_code=502, detail=result["error"])

    transcript = result.get("transcript", "") or ""

    amendment = ShipmentAmendment(
        shipment_id=shipment_id,
        agent_id=current_user.id,
        amendment_type=amendment_type,
        voice_file_url=f"blob://shipment-amendments/{file.filename}",
        voice_transcript=transcript,
        transcript_status="completed" if transcript else "failed",
        target_field=target_field,
        previous_value=previous_value,
        new_value=new_value,
        provider=result.get("provider"),
        model=result.get("model"),
    )
    db.add(amendment)
    await db.commit()
    await db.refresh(amendment)
    return _serialize(amendment)


@router.get("/shipment/{shipment_id}")
async def list_amendments(
    shipment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[Dict[str, Any]]:
    sh_q = await db.execute(
        select(Shipment).where(
            Shipment.id == shipment_id,
            Shipment.company_id == current_user.company_id,
        )
    )
    if not sh_q.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Shipment not found")

    q = await db.execute(
        select(ShipmentAmendment)
        .where(ShipmentAmendment.shipment_id == shipment_id)
        .order_by(ShipmentAmendment.created_at.desc())
    )
    return [_serialize(a) for a in q.scalars().all()]
