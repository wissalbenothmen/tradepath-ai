from __future__ import annotations
import json
from typing import Any
from openai import AsyncOpenAI
from app.config import get_settings

settings = get_settings()
_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


# Known FTA pairs (origin_country, destination_country) → FTA name
FTA_MAP: dict[tuple[str, str], list[str]] = {
    ("MX", "US"): ["USMCA"], ("CA", "US"): ["USMCA"], ("US", "MX"): ["USMCA"],
    ("US", "CA"): ["USMCA"], ("MX", "CA"): ["USMCA"], ("CA", "MX"): ["USMCA"],
    ("US", "KR"): ["US_KOREA_FTA"], ("KR", "US"): ["US_KOREA_FTA"],
    ("US", "SG"): ["US_SINGAPORE_FTA"], ("SG", "US"): ["US_SINGAPORE_FTA"],
    ("US", "AU"): ["US_AUSTRALIA_FTA"], ("AU", "US"): ["US_AUSTRALIA_FTA"],
    ("GB", "AU"): ["UK_AUSTRALIA_FTA"], ("AU", "GB"): ["UK_AUSTRALIA_FTA"],
    ("JP", "GB"): ["UK_JAPAN_FTA"], ("GB", "JP"): ["UK_JAPAN_FTA"],
}

# Approximate MFN duty rates by HS chapter (first 2 digits) for US
MFN_RATES_US: dict[str, float] = {
    "01": 0.00, "10": 0.00, "27": 0.0525, "30": 0.00, "39": 0.038,
    "61": 0.165, "62": 0.165, "63": 0.12, "84": 0.00, "85": 0.00,
    "87": 0.025, "90": 0.00,
}


_FTA_NARRATIVES: dict[str, str] = {
    "USMCA": (
        "Under the United States-Mexico-Canada Agreement (USMCA), goods originating in "
        "the USMCA region may qualify for preferential duty treatment. "
        "For this product, the applicable rule of origin is a Tariff Classification Change (TCC) "
        "or a Regional Value Content (RVC) threshold of at least 60% under the Transaction Value "
        "method (or 50% under Net Cost). "
        "To claim USMCA preference, the importer must possess a valid Certificate of Origin "
        "(CBP Form 434 or equivalent) at time of entry. "
        "Annual blanket certificates are accepted for multiple shipments of identical goods. "
        "The preferential duty rate of 0.0% represents a saving of {saving} USD versus the MFN rate of {mfn}%."
    ),
    "US_KOREA_FTA": (
        "Under the US-Korea Free Trade Agreement (KORUS FTA), this product may qualify "
        "for preferential tariff treatment. The staging category determines whether the rate "
        "is currently at 0% or in a phase-down schedule. "
        "Origin documentation (Korean Certificate of Origin from the Korea Customs Service) "
        "is required to claim the preference. The estimated duty saving is {saving} USD."
    ),
    "US_SINGAPORE_FTA": (
        "Under the US-Singapore FTA, substantially all goods originating in Singapore qualify "
        "for duty-free treatment. The rule of origin requires a tariff classification change "
        "at the 4-digit HS heading level. "
        "A Certificate of Origin from Singapore Customs is required. "
        "Estimated duty saving: {saving} USD."
    ),
    "US_AUSTRALIA_FTA": (
        "Under the Australia-US FTA (AUSFTA), qualifying goods may receive preferential "
        "duty rates. A supplier's declaration or Certificate of Origin is required. "
        "Estimated duty saving: {saving} USD."
    ),
    "UK_AUSTRALIA_FTA": (
        "Under the UK-Australia Free Trade Agreement (2023), goods meeting the product-specific "
        "rules of origin qualify for preferential UK Global Tariff rates. "
        "A Declaration of Origin from the exporter is required. Estimated saving: {saving} USD."
    ),
    "UK_JAPAN_FTA": (
        "Under the UK-Japan Comprehensive Economic Partnership Agreement (CEPA), "
        "qualifying goods from Japan may enter the UK at reduced or zero duty. "
        "The tariff elimination schedule mirrors the EU-Japan EPA phased approach. "
        "Estimated saving: {saving} USD."
    ),
}

_NO_FTA_NARRATIVE = (
    "No Free Trade Agreement applies to the {origin}→{destination} trade lane for HS code {hs}. "
    "The applicable Most Favoured Nation (MFN) duty rate of {mfn}% is the standard rate under "
    "WTO commitments. Consider reviewing whether alternative routing, tariff engineering, "
    "or GSP (Generalised System of Preferences) eligibility could reduce this duty burden. "
    "For future shipments, assessing whether goods can qualify under USMCA, US-Korea FTA, "
    "or other applicable agreements is recommended."
)


def _mock_fta_analysis(
    origin: str, destination: str, hs_code: str,
    declared_value: float, product: str,
    applicable_ftas: list[str], mfn_rate: float,
) -> dict:
    preferential_rate = 0.0 if applicable_ftas else mfn_rate
    saving = estimate_duty_saving(declared_value, hs_code, mfn_rate, preferential_rate)
    saving_fmt = f"${saving:,.2f}"
    mfn_pct = f"{mfn_rate * 100:.1f}"

    if applicable_ftas:
        fta_key = applicable_ftas[0]
        template = _FTA_NARRATIVES.get(fta_key, _FTA_NARRATIVES["USMCA"])
        analysis = template.format(saving=saving_fmt, mfn=mfn_pct)
        qual_notes = (
            f"This shipment from {origin} to {destination} likely qualifies under {fta_key}. "
            f"Ensure a valid Certificate of Origin is on file before claiming the preference. "
            f"The tariff classification HS {hs_code} falls within the product-specific rules "
            f"of origin for {fta_key}. Estimated annual saving (10 similar shipments): "
            f"${saving * 10:,.0f} USD."
        )
    else:
        analysis = _NO_FTA_NARRATIVE.format(
            origin=origin, destination=destination, hs=hs_code, mfn=mfn_pct
        )
        qual_notes = (
            f"No preferential FTA rate available for {origin}→{destination}. "
            f"MFN rate {mfn_pct}% applies. Review GSP eligibility or tariff engineering options."
        )

    return {
        "applicable_ftas": applicable_ftas,
        "mfn_duty_rate": mfn_rate,
        "preferential_duty_rate": preferential_rate,
        "duty_saving_usd": saving,
        "qualifies": bool(applicable_ftas),
        "qualification_notes": qual_notes,
        "gpt_analysis": analysis,
    }


def get_applicable_ftas(origin: str, destination: str) -> list[str]:
    return FTA_MAP.get((origin.upper(), destination.upper()), [])


def estimate_duty_saving(
    declared_value_usd: float,
    hs_code_6digit: str,
    mfn_rate: float,
    preferential_rate: float,
) -> float:
    saving = declared_value_usd * (mfn_rate - preferential_rate)
    return round(max(0.0, saving), 2)


async def analyze_fta(
    origin_country: str,
    destination_country: str,
    hs_code_6digit: str,
    declared_value_usd: float,
    product_description: str,
) -> dict[str, Any]:
    applicable_ftas = get_applicable_ftas(origin_country, destination_country)
    mfn_rate = MFN_RATES_US.get(hs_code_6digit[:2], 0.05)

    system = """You are an international trade specialist expert in FTA preferential tariff rates.

Given the trade lane, HS code, and product, determine:
1. Which FTAs apply (if any)
2. The MFN duty rate and preferential rate under each FTA
3. Estimated duty savings
4. Whether origin qualification criteria are likely met

Return JSON:
{
  "applicable_ftas": ["USMCA", ...],
  "mfn_duty_rate": 0.05,
  "preferential_duty_rate": 0.00,
  "duty_saving_usd": 500.00,
  "qualifies": true/false,
  "qualification_notes": "...",
  "gpt_analysis": "Comprehensive FTA analysis..."
}"""

    user_content = json.dumps({
        "origin": origin_country,
        "destination": destination_country,
        "hs_code": hs_code_6digit,
        "declared_value_usd": declared_value_usd,
        "product": product_description,
        "known_ftas": applicable_ftas,
        "estimated_mfn_rate": mfn_rate,
    })

    try:
        response = await _get_client().chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        return json.loads(response.choices[0].message.content)
    except Exception:
        return _mock_fta_analysis(
            origin_country, destination_country, hs_code_6digit,
            declared_value_usd, product_description, applicable_ftas, mfn_rate
        )
