from __future__ import annotations
from typing import Any

FX_RATES_TO_USD: dict[str, float] = {
    "USD": 1.0, "EUR": 1.08, "GBP": 1.27, "JPY": 0.0067, "CAD": 0.74,
    "AUD": 0.65, "CHF": 1.12, "CNY": 0.138, "INR": 0.012, "BRL": 0.20,
    "MXN": 0.058, "KRW": 0.00075, "SGD": 0.74, "HKD": 0.128, "NOK": 0.095,
    "SEK": 0.096, "DKK": 0.145, "NZD": 0.61, "ZAR": 0.054, "THB": 0.028,
}


def convert_to_usd(amount: float, currency: str) -> float:
    rate = FX_RATES_TO_USD.get(currency.upper(), 1.0)
    return round(amount * rate, 2)


# Simplified VAT rates by destination country
VAT_RATES: dict[str, float] = {
    "GB": 0.20, "DE": 0.19, "FR": 0.20, "IT": 0.22, "ES": 0.21,
    "NL": 0.21, "BE": 0.21, "SE": 0.25, "DK": 0.25, "PL": 0.23,
    "AU": 0.10, "CA": 0.05, "IN": 0.18, "BR": 0.17, "JP": 0.10,
    "US": 0.00,  # US has no federal VAT; state sales tax varies
}

# Anti-dumping duties by (HS-chapter, origin) — subset of real data
ANTI_DUMPING: dict[tuple[str, str], float] = {
    ("84", "CN"): 0.25,
    ("85", "CN"): 0.25,
    ("73", "CN"): 0.246,
    ("73", "KR"): 0.159,
    ("39", "CN"): 0.065,
}


def calculate_duties(
    cif_value_usd: float,
    fob_value_usd: float,
    duty_rate: float,
    destination_country: str,
    hs_code_6digit: str,
    origin_country: str,
    preferential_rate: float | None = None,
    anti_dumping_rate: float | None = None,
) -> dict[str, Any]:
    """
    Calculate total import duties and taxes.
    CIF basis used for duty calculation (standard for EU/UK/most countries).
    FOB basis used for US duties.
    """
    dest = destination_country.upper()
    origin = origin_country.upper()
    hs_chapter = hs_code_6digit[:2]

    # Choose basis
    duty_basis = fob_value_usd if dest == "US" else cif_value_usd
    effective_rate = preferential_rate if preferential_rate is not None else duty_rate

    basic_duty = round(duty_basis * effective_rate, 2)

    # Anti-dumping
    if anti_dumping_rate is None:
        anti_dumping_rate = ANTI_DUMPING.get((hs_chapter, origin[:2]), 0.0)
    anti_dumping_duty = round(duty_basis * anti_dumping_rate, 2)

    # VAT on (CIF + duty)
    vat_rate = VAT_RATES.get(dest, 0.0)
    vat_base = cif_value_usd + basic_duty + anti_dumping_duty
    vat_amount = round(vat_base * vat_rate, 2)

    total_duty = round(basic_duty + anti_dumping_duty, 2)
    total_tax = round(vat_amount, 2)
    total_landed_cost = round(cif_value_usd + total_duty + total_tax, 2)

    return {
        "duty_basis_usd": duty_basis,
        "effective_duty_rate": effective_rate,
        "basic_duty_usd": basic_duty,
        "anti_dumping_duty_usd": anti_dumping_duty,
        "vat_rate": vat_rate,
        "vat_amount_usd": vat_amount,
        "total_duty_usd": total_duty,
        "total_tax_usd": total_tax,
        "total_landed_cost_usd": total_landed_cost,
    }
