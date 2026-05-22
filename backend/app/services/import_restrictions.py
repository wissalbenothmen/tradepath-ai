from __future__ import annotations
from typing import Any

# High-risk country pairs (origin → destination) requiring license review
LICENSE_REQUIRED_PAIRS: set[tuple[str, str]] = {
    ("CN", "US"), ("RU", "US"), ("IR", "US"), ("KP", "US"),
    ("CN", "GB"), ("RU", "GB"), ("IR", "EU"), ("BY", "EU"),
    ("SY", "US"), ("CU", "US"), ("VE", "US"),
}

PROHIBITED_PAIRS: set[tuple[str, str]] = {
    ("KP", "US"), ("KP", "GB"), ("KP", "EU"),
    ("IR", "US"), ("SY", "US"),
}

QUOTA_COUNTRIES: set[str] = {"CN", "BD", "VN", "IN", "PK"}

QUOTA_HS_PREFIXES: set[str] = {"61", "62", "63"}  # textiles/apparel

ITAR_RESTRICTED_HS_PREFIXES: set[str] = {"87", "88", "93"}


def check_import_restrictions(
    origin_country: str,
    destination_country: str,
    hs_code_6digit: str,
    is_itar_ear: bool = False,
) -> dict[str, Any]:
    """
    Determine import restriction status for a shipment.
    Returns: status (CLEAR/LICENSE_REQUIRED/QUOTA_CHECK/PROHIBITED), reasons list
    """
    origin = origin_country.upper()[:2] if len(origin_country) >= 2 else origin_country.upper()
    dest = destination_country.upper()[:2] if len(destination_country) >= 2 else destination_country.upper()
    hs6 = hs_code_6digit[:6]

    reasons: list[str] = []

    # ITAR/EAR always requires license
    if is_itar_ear or any(hs6.startswith(p) for p in ITAR_RESTRICTED_HS_PREFIXES):
        reasons.append(f"HS {hs6} may require ITAR/EAR export license from {origin} to {dest}")

    # Prohibited country pair
    if (origin, dest) in PROHIBITED_PAIRS:
        reasons.append(f"Trade from {origin} to {dest} is prohibited under sanctions")
        return {"status": "PROHIBITED", "reasons": reasons}

    # License required
    if reasons or (origin, dest) in LICENSE_REQUIRED_PAIRS:
        if not reasons:
            reasons.append(f"Trade from {origin} to {dest} may require export/import license")
        return {"status": "LICENSE_REQUIRED", "reasons": reasons}

    # Quota check for textile/apparel from high-quota countries
    if origin in QUOTA_COUNTRIES and any(hs6.startswith(p) for p in QUOTA_HS_PREFIXES):
        reasons.append(f"HS {hs6} from {origin} may be subject to textile/apparel quotas")
        return {"status": "QUOTA_CHECK", "reasons": reasons}

    return {"status": "CLEAR", "reasons": []}
