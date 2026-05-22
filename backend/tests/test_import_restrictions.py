from __future__ import annotations
from app.services.import_restrictions import check_import_restrictions


def test_clear_standard_trade():
    result = check_import_restrictions("DE", "US", "847130", is_itar_ear=False)
    assert result["status"] == "CLEAR"
    assert result["reasons"] == []


def test_prohibited_north_korea():
    result = check_import_restrictions("KP", "US", "847130")
    assert result["status"] == "PROHIBITED"
    assert len(result["reasons"]) > 0


def test_license_required_china_to_us():
    result = check_import_restrictions("CN", "US", "847130")
    assert result["status"] == "LICENSE_REQUIRED"


def test_license_required_itar_flag():
    result = check_import_restrictions("DE", "AU", "930100", is_itar_ear=True)
    assert result["status"] == "LICENSE_REQUIRED"


def test_quota_check_textiles_from_china():
    result = check_import_restrictions("CN", "AU", "610910")
    assert result["status"] == "QUOTA_CHECK"


def test_quota_check_textiles_from_bangladesh():
    result = check_import_restrictions("BD", "GB", "620000")
    assert result["status"] == "QUOTA_CHECK"


def test_no_quota_non_textile_from_quota_country():
    result = check_import_restrictions("CN", "AU", "847130")
    # CN-AU is not in LICENSE pairs and not a textile, should be CLEAR or at most license
    assert result["status"] in ("CLEAR", "LICENSE_REQUIRED")


def test_prohibited_iran_to_us():
    result = check_import_restrictions("IR", "US", "270900")
    assert result["status"] == "PROHIBITED"
