"""Phase A — shipment-amendment voice tests for TradePath."""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient


async def _make_shipment(client: AsyncClient, broker_token: str) -> str:
    res = await client.post(
        "/api/v1/shipments",
        json={
            "origin_country": "CN",
            "destination_country": "DE",
            "transport_mode": "sea",
            "incoterms": "CIF",
            "exporter_name": "Voice Test Exporter",
            "consignee_name": "Voice Test Consignee",
            "total_value_usd": 12400.0,
            "currency": "EUR",
        },
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


@pytest.mark.asyncio
async def test_amendment_lifecycle(client: AsyncClient, broker_token: str):
    shipment_id = await _make_shipment(client, broker_token)
    headers = {"Authorization": f"Bearer {broker_token}"}

    files = {"file": ("amendment.wav", b"\x00fake_audio_bytes", "audio/wav")}
    data = {
        "amendment_type": "hs_code_revision",
        "target_field": "hs_code",
        "previous_value": "8504.40.95",
        "new_value": "8504.40.85",
    }
    up = await client.post(
        f"/api/v1/shipment-amendments/shipment/{shipment_id}/upload",
        files=files,
        data=data,
        headers=headers,
    )
    assert up.status_code == 201, up.text
    body = up.json()
    assert body["shipment_id"] == shipment_id
    assert body["transcript_status"] == "completed"
    assert body["voice_transcript"], "transcript should be populated"
    # Mock canned transcript mentions HS code / declared value
    assert ("HS code" in body["voice_transcript"]
            or "8504" in body["voice_transcript"])
    assert body["amendment_type"] == "hs_code_revision"
    assert body["target_field"] == "hs_code"
    assert body["previous_value"] == "8504.40.95"

    listed = await client.get(
        f"/api/v1/shipment-amendments/shipment/{shipment_id}",
        headers=headers,
    )
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == body["id"]


@pytest.mark.asyncio
async def test_amendment_rejects_bad_extension(client: AsyncClient, broker_token: str):
    shipment_id = await _make_shipment(client, broker_token)
    res = await client.post(
        f"/api/v1/shipment-amendments/shipment/{shipment_id}/upload",
        files={"file": ("note.txt", b"hi", "text/plain")},
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 415


@pytest.mark.asyncio
async def test_amendment_unknown_shipment_404(client: AsyncClient, broker_token: str):
    res = await client.get(
        f"/api/v1/shipment-amendments/shipment/{uuid.uuid4()}",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 404
