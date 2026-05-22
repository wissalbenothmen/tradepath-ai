"""Phase B + C tests for TradePath — voice amendment ↔ trade-document cross-validation."""
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


# ---- pure unit tests --------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_voice_claims_and_contradictions():
    from app.services.trade_amendment_analyzer import (
        extract_voice_claims,
        detect_contradictions,
        TradeAmendmentAnalyzer,
    )

    transcript = (
        "Correction on shipment TP-X: the correct HS code should be 8504.40.85, "
        "the declared value is $42,500 USD, and the country of origin is Vietnam, "
        "not China. Quantity remains 1,200 pieces."
    )
    claims = extract_voice_claims(transcript)
    assert "85044085" in claims["hs_codes"]
    assert 42500.0 in claims["values_usd"]
    assert "VNM" in claims["origins"]
    assert any(q["qty"] == 1200.0 for q in claims["quantities"])

    # Existing record disagrees on HS, value, and origin → 3 contradictions.
    line_items = [
        {
            "hs_code": "85044095",
            "country_of_origin": "CHN",
            "total_value_usd": 12400.0,
            "quantity": 1200,
            "unit": "pieces",
        },
    ]
    documents = [{"ocr_extracted": {"hs_code": "85044095", "total_value": 12400.0}}]
    analyzer = TradeAmendmentAnalyzer()
    result = await analyzer.analyze(transcript, line_items, documents)
    assert result["mode"] == "deterministic"
    types = {c["type"] for c in result["contradictions"]}
    assert "hs_code_revision" in types
    assert "declared_value_drift" in types
    assert "country_of_origin_revision" in types
    # Talking points get severity tags
    severities = {tp["severity"] for tp in result["talking_points"]}
    assert "high" in severities or "critical" in severities


@pytest.mark.asyncio
async def test_no_contradictions_when_voice_matches_record():
    from app.services.trade_amendment_analyzer import TradeAmendmentAnalyzer
    transcript = (
        "Confirming HS code 8504.40.95, declared value $12,400 USD, country of "
        "origin China. No changes."
    )
    line_items = [{
        "hs_code": "85044095",
        "country_of_origin": "CHN",
        "total_value_usd": 12400.0,
        "quantity": 1200,
        "unit": "pieces",
    }]
    analyzer = TradeAmendmentAnalyzer()
    result = await analyzer.analyze(transcript, line_items, [])
    assert result["contradictions"] == []
    topics = {tp["topic"] for tp in result["talking_points"]}
    assert "no_contradictions" in topics


@pytest.mark.asyncio
async def test_empty_transcript_no_transcript_mode():
    from app.services.trade_amendment_analyzer import TradeAmendmentAnalyzer
    analyzer = TradeAmendmentAnalyzer()
    result = await analyzer.analyze("", [], [])
    assert result["mode"] == "no_transcript"
    assert result["contradictions"] == []


# ---- endpoint tests ---------------------------------------------------------


async def _make_shipment_with_line_item_and_amendment(
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

    # Inject a line item + (optional) voice amendment directly into the DB.
    from app.models.shipment_line_item import ShipmentLineItem
    from app.models.shipment_amendment import ShipmentAmendment
    li = ShipmentLineItem(
        shipment_id=uuid.UUID(shipment_id),
        line_number=1,
        product_description="Industrial widget",
        hs_code="85044095",
        country_of_origin="CHN",
        quantity=1200.0,
        unit="pieces",
        unit_value_usd=10.33,
        total_value_usd=12400.0,
    )
    db_session.add(li)
    if transcript is not None:
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
async def test_amendment_cross_validate_endpoint(
    client: AsyncClient, broker_token: str, db_session,
):
    transcript = (
        "Correction: the correct HS code is 8504.40.85, declared value $42,500 USD, "
        "country of origin Vietnam."
    )
    shipment_id = await _make_shipment_with_line_item_and_amendment(
        client, broker_token, db_session, transcript,
    )
    res = await client.post(
        f"/api/v1/shipments/{shipment_id}/amendment-cross-validate",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "completed"
    assert body["mode"] == "deterministic"
    assert body["line_items_checked"] == 1
    types = {c["type"] for c in body["contradictions"]}
    assert "hs_code_revision" in types
    assert "declared_value_drift" in types
    assert "country_of_origin_revision" in types


@pytest.mark.asyncio
async def test_amendment_cross_validate_no_transcript(
    client: AsyncClient, broker_token: str, db_session,
):
    shipment_id = await _make_shipment_with_line_item_and_amendment(
        client, broker_token, db_session, transcript=None,
    )
    res = await client.post(
        f"/api/v1/shipments/{shipment_id}/amendment-cross-validate",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 200, res.text
    assert res.json()["status"] == "no_transcript"


@pytest.mark.asyncio
async def test_amendment_brief_pdf_renders(
    client: AsyncClient, broker_token: str, db_session,
):
    transcript = (
        "Correction on HS code to 8504.40.85, declared value $42,500 USD. Origin Vietnam."
    )
    shipment_id = await _make_shipment_with_line_item_and_amendment(
        client, broker_token, db_session, transcript,
    )
    pdf = await client.get(
        f"/api/v1/shipments/{shipment_id}/amendment-brief.pdf",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"
    assert "tradepath-amendment-" in pdf.headers.get("content-disposition", "")
    assert pdf.headers.get("x-tradepath-mode") == "deterministic"


@pytest.mark.asyncio
async def test_amendment_cross_validate_unknown_shipment_404(
    client: AsyncClient, broker_token: str,
):
    res = await client.post(
        "/api/v1/shipments/00000000-0000-0000-0000-000000000000/amendment-cross-validate",
        headers={"Authorization": f"Bearer {broker_token}"},
    )
    assert res.status_code == 404
