from __future__ import annotations
import pytest
from app.services.duty_calculator import calculate_duties, convert_to_usd
from app.services.document_ocr import convert_to_usd as ocr_convert


def test_basic_duty_calculation():
    result = calculate_duties(
        cif_value_usd=10000.0,
        fob_value_usd=9000.0,
        duty_rate=0.05,
        destination_country="GB",
        hs_code_6digit="847130",
        origin_country="CN",
    )
    assert result["basic_duty_usd"] == pytest.approx(500.0, rel=1e-3)
    assert result["vat_rate"] == 0.20
    assert result["total_duty_usd"] >= 500.0


def test_us_uses_fob_basis():
    result = calculate_duties(
        cif_value_usd=10000.0,
        fob_value_usd=8000.0,
        duty_rate=0.05,
        destination_country="US",
        hs_code_6digit="847130",
        origin_country="DE",
    )
    # US duty = FOB * rate = 8000 * 0.05 = 400
    assert result["duty_basis_usd"] == 8000.0
    assert result["basic_duty_usd"] == pytest.approx(400.0)


def test_eu_uses_cif_basis():
    result = calculate_duties(
        cif_value_usd=10000.0,
        fob_value_usd=8000.0,
        duty_rate=0.038,
        destination_country="DE",
        hs_code_6digit="390000",
        origin_country="US",
    )
    assert result["duty_basis_usd"] == 10000.0


def test_preferential_rate_reduces_duty():
    mfn = calculate_duties(10000, 9000, 0.10, "GB", "847130", "CN")
    pref = calculate_duties(10000, 9000, 0.10, "GB", "847130", "CN", preferential_rate=0.0)
    assert pref["basic_duty_usd"] < mfn["basic_duty_usd"]


def test_zero_duty_rate():
    result = calculate_duties(5000, 4500, 0.0, "US", "090111", "BR")
    assert result["basic_duty_usd"] == 0.0


def test_anti_dumping_auto_detected_cn_steel():
    result = calculate_duties(10000, 9000, 0.02, "US", "730000", "CN")
    assert result["anti_dumping_duty_usd"] > 0.0


def test_total_landed_cost():
    result = calculate_duties(10000, 9500, 0.05, "FR", "847130", "US")
    expected = 10000 + result["total_duty_usd"] + result["total_tax_usd"]
    assert result["total_landed_cost_usd"] == pytest.approx(expected, rel=1e-3)


def test_fx_conversion_eur():
    usd = ocr_convert(100.0, "EUR")
    assert usd == pytest.approx(108.0, rel=0.01)


def test_fx_conversion_gbp():
    usd = ocr_convert(100.0, "GBP")
    assert usd == pytest.approx(127.0, rel=0.01)


def test_fx_conversion_unknown_defaults_to_1():
    usd = ocr_convert(100.0, "XYZ")
    assert usd == pytest.approx(100.0)
