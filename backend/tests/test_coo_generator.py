from __future__ import annotations
import pytest
from app.services.coo_generator import calculate_rvc


def test_rvc_basic_usmca():
    result = calculate_rvc(10000.0, 2000.0, "USMCA")
    assert result["rvc_percentage"] == pytest.approx(80.0)
    assert result["passes"] is True  # 80% >= 75% USMCA threshold


def test_rvc_fails_threshold():
    result = calculate_rvc(10000.0, 7000.0, "USMCA")
    assert result["rvc_percentage"] == pytest.approx(30.0)
    assert result["passes"] is False


def test_rvc_zero_transaction_value():
    result = calculate_rvc(0.0, 0.0)
    assert result["rvc_percentage"] == 0.0
    assert result["passes"] is False


def test_rvc_default_threshold():
    result = calculate_rvc(10000.0, 6000.0, "UNKNOWN_FTA")
    assert result["threshold"] == 35.0  # DEFAULT threshold
    assert result["rvc_percentage"] == pytest.approx(40.0)
    assert result["passes"] is True


def test_rvc_wholly_originating():
    result = calculate_rvc(10000.0, 0.0, "USMCA")
    assert result["rvc_percentage"] == pytest.approx(100.0)
    assert result["passes"] is True


def test_rvc_calculation_includes_breakdown():
    result = calculate_rvc(10000.0, 3000.0, "CPTPP")
    assert "transaction_value" in result
    assert "non_originating_materials" in result
    assert result["method"] == "transaction_value"


@pytest.mark.asyncio
async def test_analyze_origin_calls_gpt():
    import json
    from unittest.mock import AsyncMock, patch

    mock_data = {
        "origin_criterion": "tariff_shift",
        "qualifies_for_preference": True,
        "origin_analysis": "The product undergoes tariff shift under USMCA.",
        "document_content": "CERTIFICATE OF ORIGIN\nExporter: ACME Corp\n...",
        "preferential_duty_saving_usd": 1500.0,
        "rvc_percentage": None,
        "warnings": [],
    }

    mock_message = AsyncMock()
    mock_message.content = json.dumps(mock_data)
    mock_choice = AsyncMock()
    mock_choice.message = mock_message
    mock_completion = AsyncMock()
    mock_completion.choices = [mock_choice]

    with patch("app.services.coo_generator._get_client") as mock_fn:
        from app.services.coo_generator import analyze_origin_and_generate_coo
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_fn.return_value = mock_client

        result = await analyze_origin_and_generate_coo(
            shipment_data={"origin_country": "MX", "destination_country": "US"},
            line_items=[],
            coo_format="usmca",
        )

    assert result["origin_criterion"] == "tariff_shift"
    assert result["qualifies_for_preference"] is True
