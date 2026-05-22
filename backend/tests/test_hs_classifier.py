from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, patch
from app.services.hs_classifier import classify_hs_code, _flag_itar_ear, _normalize


def test_flag_itar_ear_by_keyword():
    assert _flag_itar_ear("military grade firearm component", "930190") is True


def test_flag_itar_ear_by_hs_prefix():
    assert _flag_itar_ear("optical scope", "930400") is True


def test_no_itar_flag_civilian():
    assert _flag_itar_ear("cotton t-shirt", "610910") is False


def test_normalize_accents():
    result = _normalize("Müller GmbH")
    assert "MULLER" in result or "MLLER" in result  # accent stripped


def test_normalize_special_chars():
    assert "HEZBOLLAH" == _normalize("Hezbollah")


@pytest.mark.asyncio
async def test_classify_returns_required_fields():
    mock_response_data = {
        "hs_code_6digit": "847130",
        "hs_code_us_hts": "8471300100",
        "hs_code_eu_taric": "8471300000",
        "hs_code_uk_gt": "8471300000",
        "confidence": 0.92,
        "gri_rules_applied": [1, 6],
        "duty_rate_us": 0.0,
        "duty_rate_eu": 0.0,
        "anti_dumping_duty": None,
        "top_candidates": [],
        "gpt_reasoning": "GRI 1: Heading 8471 covers automatic data processing machines.",
    }

    import json
    mock_message = AsyncMock()
    mock_message.content = json.dumps(mock_response_data)
    mock_choice = AsyncMock()
    mock_choice.message = mock_message
    mock_completion = AsyncMock()
    mock_completion.choices = [mock_choice]

    with patch("app.services.hs_classifier._get_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_client_fn.return_value = mock_client

        result = await classify_hs_code(
            product_description="Laptop computer portable",
            materials="aluminum, plastic, lithium battery",
            intended_use="personal computing",
        )

    assert result["hs_code_6digit"] == "847130"
    assert result["confidence"] == 0.92
    assert result["is_itar_ear_flagged"] == "false"
    assert result["top_candidates"] == []


@pytest.mark.asyncio
async def test_classify_low_confidence_keeps_candidates():
    mock_response_data = {
        "hs_code_6digit": "392310",
        "hs_code_us_hts": "3923100000",
        "hs_code_eu_taric": "3923100000",
        "hs_code_uk_gt": "3923100000",
        "confidence": 0.65,
        "gri_rules_applied": [1, 3],
        "duty_rate_us": 0.03,
        "duty_rate_eu": 0.065,
        "anti_dumping_duty": None,
        "top_candidates": [
            {"hs_code": "392310", "description": "Boxes of plastic", "confidence": 0.65},
            {"hs_code": "392390", "description": "Other plastic articles", "confidence": 0.50},
            {"hs_code": "481900", "description": "Cartons of paper", "confidence": 0.35},
        ],
        "gpt_reasoning": "Ambiguous between plastic and paper containers.",
    }

    import json
    mock_message = AsyncMock()
    mock_message.content = json.dumps(mock_response_data)
    mock_choice = AsyncMock()
    mock_choice.message = mock_message
    mock_completion = AsyncMock()
    mock_completion.choices = [mock_choice]

    with patch("app.services.hs_classifier._get_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_client_fn.return_value = mock_client

        result = await classify_hs_code("plastic container box")

    assert result["confidence"] == 0.65
    assert len(result["top_candidates"]) == 3


@pytest.mark.asyncio
async def test_classify_high_confidence_clears_candidates():
    mock_response_data = {
        "hs_code_6digit": "090111",
        "hs_code_us_hts": "0901110015",
        "hs_code_eu_taric": "0901110000",
        "hs_code_uk_gt": "0901110000",
        "confidence": 0.98,
        "gri_rules_applied": [1],
        "duty_rate_us": 0.0,
        "duty_rate_eu": 0.0,
        "anti_dumping_duty": None,
        "top_candidates": [{"hs_code": "090111", "description": "Coffee", "confidence": 0.98}],
        "gpt_reasoning": "Clearly coffee beans.",
    }

    import json
    mock_message = AsyncMock()
    mock_message.content = json.dumps(mock_response_data)
    mock_choice = AsyncMock()
    mock_choice.message = mock_message
    mock_completion = AsyncMock()
    mock_completion.choices = [mock_choice]

    with patch("app.services.hs_classifier._get_client") as mock_client_fn:
        mock_client = AsyncMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_completion)
        mock_client_fn.return_value = mock_client

        result = await classify_hs_code("green coffee beans unroasted")

    assert result["confidence"] == 0.98
    assert result["top_candidates"] == []
