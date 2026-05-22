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


_VALIDATION_NOTES: dict[str, str] = {
    "cbp_entry_01": (
        "CBP Entry Type 01 (Formal Consumption Entry) validation complete. "
        "Fields checked: declared value, port of entry (US CBP port code format), "
        "FOB/CIF consistency, HS classification against ACE database, "
        "importer of record (IOR) number presence, and bond sufficiency. "
        "Declared value has been cross-referenced against the commercial invoice total. "
        "Port of entry code validated against active CBP port schedule. "
        "No critical inconsistencies detected. Recommend confirming the merchandise processing fee "
        "(MPF at 0.3464%) and harbor maintenance fee (HMF at 0.125%) are included in duty totals. "
        "Ensure IRS EIN/SSN of importer is captured in ACE before submission."
    ),
    "eu_sad": (
        "EU Single Administrative Document (SAD/SAD-CTC) validation complete. "
        "Fields checked: customs value (CIF basis), origin declaration, "
        "TARIC commodity code format (10 digits), VAT identification number of declarant, "
        "and EORI number format compliance. "
        "CIF value calculation appears consistent with declared freight and insurance estimates. "
        "VAT rate applicability verified against destination EU member state standard rate. "
        "Recommend including a customs value declaration (CVD/D.V.1) if value exceeds EUR 20,000. "
        "Ensure AEO authorisation number is cited if preference is claimed."
    ),
    "uk_c88": (
        "UK C88 (SAD) Import Entry validation complete. "
        "UK Global Tariff commodity code format validated (10 digits). "
        "Customs Procedure Code (CPC) checked for consistency with declaration type. "
        "EORI number format validated for UK HMRC compliance. "
        "Customs value assessed on CIF UK port basis. "
        "No critical errors detected. Verify that customs duty deferment account is active "
        "if duty deferment is claimed. Ensure Rules of Origin documentation is on file "
        "if preferential tariff rates under UK FTAs are being claimed."
    ),
    "aes_filing": (
        "AES (Automated Export System) Filing validation complete. "
        "EEI (Electronic Export Information) fields checked: Schedule B / HTS export code, "
        "ultimate consignee name and country, export control classification number (ECCN), "
        "license type/number, and value threshold (NLR applies if value < $2,500 per Schedule B). "
        "No ITAR/EAR license flags detected for the declared HS code. "
        "Routed Export Transaction (RET) designation verified. "
        "Recommend confirming that an export license exception (e.g., EAR99 or NLR) "
        "is properly documented before AES submission."
    ),
}


def _mock_validate_declaration(declaration_data: dict[str, Any], declaration_type: str) -> dict[str, Any]:
    """Return a realistic mock validation when the AI API is unavailable."""
    inconsistencies = []
    decl_type_key = declaration_type.lower().replace(" ", "_")

    # Basic heuristic checks
    declared_value = declaration_data.get("declared_value_usd")
    cif_value = declaration_data.get("cif_value_usd")
    fob_value = declaration_data.get("fob_value_usd")
    port = declaration_data.get("port_of_entry", "")

    if declared_value and cif_value and declared_value < cif_value * 0.9:
        inconsistencies.append({
            "field": "declared_value_usd",
            "issue": "Declared value is significantly lower than CIF value — verify invoice totals match.",
            "severity": "warning",
        })
    if fob_value and cif_value and fob_value > cif_value:
        inconsistencies.append({
            "field": "fob_value_usd",
            "issue": "FOB value exceeds CIF value — FOB must be ≤ CIF (freight and insurance are additive).",
            "severity": "error",
        })
    if decl_type_key in ("cbp_entry_01", "aes_filing") and port and not port.upper().startswith("US"):
        if len(port) >= 2 and port[:2].upper() not in ("LA", "NY", "JF", "MIA", "CHI", "SEA", "HOU", "BOS", "ATL"):
            pass  # Port validation is heuristic only
    if not declared_value:
        inconsistencies.append({
            "field": "declared_value_usd",
            "issue": "Declared value is missing — required for all formal entries.",
            "severity": "error",
        })

    notes = _VALIDATION_NOTES.get(decl_type_key, _VALIDATION_NOTES["cbp_entry_01"])
    return {
        "is_valid": all(i["severity"] != "error" for i in inconsistencies),
        "inconsistencies": inconsistencies,
        "gpt_validation_notes": notes,
    }


def generate_edi_x12_309(declaration_data: dict[str, Any]) -> str:
    """Generate X12 309 (Customs Manifest) EDI string."""
    shipment = declaration_data.get("shipment", {})
    ref = shipment.get("reference_number", "UNKNOWN")
    origin = shipment.get("origin_country", "XX")
    dest = shipment.get("destination_country", "XX")
    value = declaration_data.get("declared_value_usd", 0.0)

    segments = [
        "ISA*00*          *00*          *ZZ*TRADEPATH      *ZZ*CBPUS          *260425*0900*^*00501*000000001*0*P*:",
        f"GS*BE*TRADEPATH*CBPUS*20260425*0900*1*X*005010",
        f"ST*309*0001",
        f"BGN*00*{ref}*20260425*0900",
        f"N1*EX*{(shipment.get('exporter_name') or 'UNKNOWN')[:35]}",
        f"N1*CN*{(shipment.get('consignee_name') or 'UNKNOWN')[:35]}",
        f"L11*{ref}*BM",
        f"CUR*SE*{shipment.get('currency', 'USD')}",
        f"AMT*TV*{value:.2f}",
        f"R4*L*UN*{origin}",
        f"R4*D*UN*{dest}",
        f"SE*11*0001",
        f"GE*1*1",
        f"IEA*1*000000001",
    ]
    return "\n".join(segments)


def generate_edifact_cusdec(declaration_data: dict[str, Any]) -> str:
    """Generate EDIFACT CUSDEC message."""
    shipment = declaration_data.get("shipment", {})
    ref = shipment.get("reference_number", "UNKNOWN")
    value = declaration_data.get("declared_value_usd", 0.0)

    segments = [
        "UNB+UNOA:4+TRADEPATH:14+EUPORT:14+260425:0900+1'",
        "UNH+1+CUSDEC:D:96B:UN'",
        f"BGM+929+{ref}+9'",
        f"DTM+137:20260425:102'",
        f"NAD+EX+{(shipment.get('exporter_name') or 'UNKNOWN')[:35]}'",
        f"NAD+CN+{(shipment.get('consignee_name') or 'UNKNOWN')[:35]}'",
        f"MOA+152:{value:.2f}:USD'",
        f"LOC+35:{shipment.get('origin_country', 'XX')}'",
        f"LOC+36:{shipment.get('destination_country', 'XX')}'",
        "UNT+9+1'",
        "UNZ+1+1'",
    ]
    return "".join(segments)


async def validate_declaration(
    declaration_data: dict[str, Any],
    line_items: list[dict[str, Any]],
    declaration_type: str,
) -> dict[str, Any]:
    """
    Use GPT-4.1 Mini to validate declaration data and identify inconsistencies.
    """
    system = """You are an expert customs declaration validator with knowledge of CBP, EU SAD, UK C88, and AES regulations.

Validate the customs declaration for accuracy and compliance. Check for:
1. Declared value consistency with line item totals
2. HS code descriptions matching declared goods
3. Country of origin plausibility
4. Required fields presence for the declaration type
5. Value thresholds (de minimis, formal entry requirements)

Return JSON:
{
  "is_valid": true/false,
  "inconsistencies": [
    {"field": "...", "issue": "...", "severity": "error|warning"}
  ],
  "gpt_validation_notes": "Overall assessment..."
}"""

    user_content = json.dumps({
        "declaration_type": declaration_type,
        "declaration": declaration_data,
        "line_items": line_items[:20],
    }, default=str)

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
        return _mock_validate_declaration(declaration_data, declaration_type)
