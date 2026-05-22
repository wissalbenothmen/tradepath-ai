from __future__ import annotations
import pytest
from app.services.denied_party_screening import (
    screen_party, _name_similarity_score, _soundex, _normalize,
    CLEAR_THRESHOLD, POTENTIAL_THRESHOLD,
)


def test_soundex_basic():
    assert _soundex("SMITH") == _soundex("SMYTH")


def test_soundex_kim():
    assert _soundex("KIM") == "K500"


def test_normalize_strips_accents():
    result = _normalize("Hézbollah")
    assert "H" in result


def test_normalize_special_chars():
    assert _normalize("Al-Qaeda") == "AL QAEDA"


def test_exact_match_scores_high():
    score = _name_similarity_score("KIM JONG UN", "KIM JONG UN")
    assert score >= 95.0


def test_typo_scores_high():
    score = _name_similarity_score("HEZBOLLAH", "HEZBOLAH")
    assert score >= CLEAR_THRESHOLD


def test_different_name_scores_low():
    score = _name_similarity_score("APPLE INC", "HEZBOLLAH")
    assert score < CLEAR_THRESHOLD


def test_partial_name_match():
    score = _name_similarity_score("IRAN AIR CARGO", "IRAN AIR")
    assert score >= 60.0


@pytest.mark.asyncio
async def test_clear_party():
    result = await screen_party("APPLE CORPORATION", "US")
    assert result["overall_result"] == "clear"
    assert result["highest_score"] < CLEAR_THRESHOLD


@pytest.mark.asyncio
async def test_positive_match_sdn():
    result = await screen_party("KIM JONG UN", "KP")
    assert result["overall_result"] == "positive_match"
    assert result["highest_score"] >= POTENTIAL_THRESHOLD
    assert len(result["matches"]) > 0


@pytest.mark.asyncio
async def test_potential_match_near_name():
    result = await screen_party("HEZBOLAH", "LB")
    assert result["overall_result"] in ("potential_match", "positive_match")


@pytest.mark.asyncio
async def test_lists_checked_returned():
    result = await screen_party("SOME COMPANY", "US", lists_to_check=["ofac_sdn"])
    assert result["lists_checked"] == ["ofac_sdn"]


@pytest.mark.asyncio
async def test_matches_sorted_by_score():
    result = await screen_party("HEZBOLLAH", "LB")
    if len(result["matches"]) > 1:
        scores = [m["score"] for m in result["matches"]]
        assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_country_boost_increases_score():
    result_no_country = await screen_party("KIM JONG UN")
    result_with_country = await screen_party("KIM JONG UN", "KP")
    assert result_with_country["highest_score"] >= result_no_country["highest_score"]
