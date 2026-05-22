"""Phase E test for TradePath — voice-records list endpoint."""
from __future__ import annotations

import os
import uuid

import pytest
from httpx import AsyncClient


@pytest.fixture(autouse=True)
def _mock_fraud_gpt():
    os.environ["MOCK_FRAUD_GPT"] = "true"
    yield
    os.environ.pop("MOCK_FRAUD_GPT", None)


async def _make_shipment_with_amendment(
    client: AsyncClient, broker_token: str, db_session, transcript: str | None,
) -> str:
    res = await client.post(
        "/api/v1/shipments",
        json={
            "origin_country": "CN",
            "destination_country": "US",
            "transport_mode": "sea",
            "exporter_name": "Test Exporter",
            "importer_name": "Test Importer",
            "total_value_usd": 12400.0,
        },
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 201, res.text
    shipment_id = res.json()["id"]

    if transcript is not None:
        from app.models.shipment_amendment import ShipmentAmendment
        am = ShipmentAmendment(
            shipment_id=uuid.UUID(shipment_id),
            voice_file_url="blob://amendments/test.mp3",
            voice_transcript=transcript,
            transcript_status="completed",
            provider="deepinfra",
            model="openai/whisper-large-v3",
            status="pending_review",
        )
        db_session.add(am)
        await db_session.commit()
    return shipment_id


@pytest.mark.asyncio
async def test_voice_records_returns_persisted_transcript(
    client: AsyncClient, broker_token: str, db_session,
):
    transcript = "Correction: HS code should be 8504.40.85. Declared value $42,500 USD."
    shipment_id = await _make_shipment_with_amendment(client, broker_token, db_session, transcript)
    res = await client.get(
        f"/api/v1/shipments/{shipment_id}/voice-records",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert isinstance(body, list)
    assert len(body) == 1
    rec = body[0]
    assert rec["voice_transcript"] == transcript
    assert rec["transcript_status"] == "completed"
    assert rec["provider"] == "deepinfra"
    assert rec["created_at"] is not None


@pytest.mark.asyncio
async def test_voice_records_empty_when_no_amendment(
    client: AsyncClient, broker_token: str, db_session,
):
    shipment_id = await _make_shipment_with_amendment(client, broker_token, db_session, transcript=None)
    res = await client.get(
        f"/api/v1/shipments/{shipment_id}/voice-records",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 200
    assert res.json() == []


@pytest.mark.asyncio
async def test_voice_records_unknown_shipment_404(
    client: AsyncClient, broker_token: str,
):
    res = await client.get(
        "/api/v1/shipments/00000000-0000-0000-0000-000000000000/voice-records",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 404
