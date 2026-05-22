"""Phase B — voice shipment-amendment ↔ trade-document OCR cross-validation.

Per the PDF spec for project_07 (TradePath AI):
    "Detects contradictions between agent voice amendments and the underlying
     commercial-invoice / BOL / certificate-of-origin OCR; flags HS-code,
     value, quantity, and origin-country discrepancies; generates a
     customs-audit-ready amendment brief."

This service:
- Reads the latest voice shipment-amendment transcript for a shipment
- Extracts the amendment's quantitative claims (HS codes, monetary values,
  quantities, country-of-origin codes, weights)
- Compares against the underlying line items + OCR-extracted document fields
- Returns:
    voice_claims      — what the voice amendment asserts
    document_state    — what the existing record says
    contradictions    — value/HS/quantity/origin mismatches
    missing_evidence  — voice claim with no supporting line item or doc field
    talking_points    — customs-audit-ready bullets

Falls back to a deterministic rule-based analyzer when MOCK_FRAUD_GPT=true
or when OPENAI_API_KEY is empty (offline-safe tests).
"""
from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional, Tuple

import openai

from app.config import get_settings


# --- Voice-extraction patterns ----------------------------------------------

_HS_RE = re.compile(r"\b(\d{4}\.?\d{2}(?:\.?\d{2})?)\b")
_MONEY_RE = re.compile(
    r"(?:\$|usd\s*)?(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\s*(?:usd|dollars?|us\s+dollars)?",
    re.IGNORECASE,
)
_QTY_RE = re.compile(
    r"\b(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\s*(units?|pieces?|pcs?|cartons?|pallets?|kg|kilograms?|tons?|tonnes?|lbs?|pounds?)\b",
    re.IGNORECASE,
)
_COUNTRY_RE = re.compile(
    r"\b(?:country\s+of\s+origin\s+is\s+|origin\s+(?:is\s+|country\s+))?"
    r"(usa|us|united\s+states|china|prc|mexico|canada|germany|japan|south\s+korea|"
    r"korea|vietnam|india|france|italy|uk|united\s+kingdom|britain|netherlands|"
    r"belgium|spain|brazil|taiwan)\b",
    re.IGNORECASE,
)
_COUNTRY_TO_ISO = {
    "usa": "USA", "us": "USA", "united states": "USA",
    "china": "CHN", "prc": "CHN",
    "mexico": "MEX", "canada": "CAN", "germany": "DEU", "japan": "JPN",
    "south korea": "KOR", "korea": "KOR", "vietnam": "VNM", "india": "IND",
    "france": "FRA", "italy": "ITA", "uk": "GBR", "united kingdom": "GBR",
    "britain": "GBR", "netherlands": "NLD", "belgium": "BEL", "spain": "ESP",
    "brazil": "BRA", "taiwan": "TWN",
}


def _clean_num(raw: str) -> Optional[float]:
    if not raw:
        return None
    s = raw.replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def extract_voice_claims(transcript: str) -> Dict[str, Any]:
    """Pull HS codes, money amounts, quantities, origin countries from the voice transcript."""
    if not transcript:
        return {"hs_codes": [], "values_usd": [], "quantities": [], "origins": []}

    hs_codes = sorted({m.group(1).replace(".", "") for m in _HS_RE.finditer(transcript)})

    # Money: only keep numbers with $ prefix OR explicit USD/dollar suffix to reduce false positives.
    values: list[float] = []
    money_pat = re.compile(
        r"\$\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)|"
        r"(\d{1,3}(?:[,\s]\d{3})*(?:\.\d+)?)\s*(?:usd|dollars?|us\s+dollars)\b",
        re.IGNORECASE,
    )
    for m in money_pat.finditer(transcript):
        raw = m.group(1) or m.group(2)
        v = _clean_num(raw)
        if v is not None:
            values.append(v)

    quantities: list[dict] = []
    for m in _QTY_RE.finditer(transcript):
        q = _clean_num(m.group(1))
        unit = m.group(2).lower().rstrip("s")
        if q is not None:
            quantities.append({"qty": q, "unit": unit})

    origins: list[str] = []
    for m in _COUNTRY_RE.finditer(transcript):
        country_phrase = re.sub(r"\s+", " ", m.group(1).lower()).strip()
        iso = _COUNTRY_TO_ISO.get(country_phrase)
        if iso and iso not in origins:
            origins.append(iso)

    return {
        "hs_codes": hs_codes,
        "values_usd": values,
        "quantities": quantities,
        "origins": origins,
    }


def _document_state(line_items: List[Dict[str, Any]], documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate the canonical record state — what the line items + docs claim today."""
    hs_codes = sorted({li.get("hs_code") for li in line_items if li.get("hs_code")})
    values = [li.get("total_value_usd") for li in line_items if li.get("total_value_usd") is not None]
    quantities = [
        {"qty": li.get("quantity"), "unit": (li.get("unit") or "").lower()}
        for li in line_items if li.get("quantity") is not None
    ]
    origins = sorted({li.get("country_of_origin") for li in line_items if li.get("country_of_origin")})

    # Pull any extra HS / value hints from OCR-extracted JSON if present
    doc_hs: list[str] = []
    doc_values: list[float] = []
    for d in documents:
        ocr = d.get("ocr_extracted") or {}
        if isinstance(ocr, dict):
            for k in ("hs_code", "hs_codes", "tariff_code"):
                v = ocr.get(k)
                if isinstance(v, str):
                    doc_hs.append(v.replace(".", ""))
                elif isinstance(v, list):
                    doc_hs.extend([str(x).replace(".", "") for x in v])
            for k in ("total_value", "invoice_total", "value_usd"):
                v = ocr.get(k)
                if isinstance(v, (int, float)):
                    doc_values.append(float(v))
                elif isinstance(v, str):
                    f = _clean_num(v)
                    if f is not None:
                        doc_values.append(f)

    return {
        "line_item_hs_codes": hs_codes,
        "document_hs_codes": sorted(set(doc_hs)),
        "line_item_values_usd": values,
        "document_values_usd": doc_values,
        "quantities": quantities,
        "origins": origins,
        "line_item_count": len(line_items),
        "document_count": len(documents),
    }


def _diff_pct(a: float, b: float) -> float:
    if b == 0:
        return float("inf") if a != 0 else 0.0
    return abs(a - b) / abs(b)


def detect_contradictions(
    voice: Dict[str, Any], state: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Return concrete value/HS/quantity/origin mismatches."""
    out: list[dict] = []

    # HS-code contradiction: voice asserts a code not in any line item or document.
    voice_hs = set(voice.get("hs_codes", []))
    record_hs = set(state.get("line_item_hs_codes", [])) | set(state.get("document_hs_codes", []))
    new_codes = voice_hs - {c.replace(".", "") for c in record_hs}
    if new_codes and record_hs:
        out.append({
            "type": "hs_code_revision",
            "voice_codes": sorted(new_codes),
            "record_codes": sorted(record_hs),
            "severity": "high",
            "description": (
                "Voice amendment introduces HS code(s) not present in the line items "
                "or the underlying commercial invoice — customs may treat this as a "
                "tariff-shift attempt; requires written justification."
            ),
        })

    # Value contradiction: voice claims a dollar value materially different from the record total.
    voice_vals = voice.get("values_usd", []) or []
    record_total = sum(state.get("line_item_values_usd") or [0.0])
    for v in voice_vals:
        if record_total and _diff_pct(v, record_total) > 0.10:
            out.append({
                "type": "declared_value_drift",
                "voice_value_usd": v,
                "record_total_usd": record_total,
                "diff_pct": round(_diff_pct(v, record_total) * 100, 2),
                "severity": "critical" if _diff_pct(v, record_total) > 0.25 else "high",
                "description": (
                    "Voice amendment changes the declared shipment value by more than 10% — "
                    "customs may flag for valuation audit; document the basis for the change."
                ),
            })
            break

    # Quantity contradiction: voice unit mismatches the record unit (e.g. kg vs lbs).
    voice_units = {q["unit"] for q in voice.get("quantities", []) if q.get("unit")}
    record_units = {(q.get("unit") or "").lower() for q in state.get("quantities", []) if q.get("unit")}
    if voice_units and record_units and voice_units.isdisjoint(record_units):
        out.append({
            "type": "quantity_unit_mismatch",
            "voice_units": sorted(voice_units),
            "record_units": sorted(record_units),
            "severity": "high",
            "description": (
                "Voice amendment expresses quantities in different units than the existing "
                "record; manifest reconciliation required before re-filing."
            ),
        })

    # Origin contradiction: voice asserts an origin not in any line item.
    voice_origins = set(voice.get("origins", []))
    record_origins = set(state.get("origins", []))
    new_origins = voice_origins - record_origins
    if new_origins and record_origins:
        out.append({
            "type": "country_of_origin_revision",
            "voice_origins": sorted(new_origins),
            "record_origins": sorted(record_origins),
            "severity": "critical",
            "description": (
                "Voice amendment changes country of origin — material impact on duty rate, "
                "FTA eligibility, and AD/CVD exposure; do not file until confirmed in writing."
            ),
        })

    return out


def _missing_evidence(voice: Dict[str, Any], state: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Voice claims with no supporting line item / document field."""
    out: list[dict] = []
    if voice.get("hs_codes") and not state.get("line_item_hs_codes") and not state.get("document_hs_codes"):
        out.append({
            "claim": "hs_code",
            "voice_values": voice["hs_codes"],
            "note": "No HS code on file in line items or OCR-extracted documents.",
        })
    if voice.get("values_usd") and not state.get("line_item_values_usd"):
        out.append({
            "claim": "declared_value",
            "voice_values": voice["values_usd"],
            "note": "No declared values on file; the voice amendment is establishing them.",
        })
    if voice.get("origins") and not state.get("origins"):
        out.append({
            "claim": "country_of_origin",
            "voice_values": voice["origins"],
            "note": "No country-of-origin on file; require certificate of origin for the destination market.",
        })
    return out


class TradeAmendmentAnalyzer:
    """Cross-validate voice shipment amendments against trade-document OCR + line items."""

    def __init__(self) -> None:
        settings = get_settings()
        self.mock_mode = (
            os.environ.get("MOCK_FRAUD_GPT", "").lower() in {"1", "true", "yes"}
            or not getattr(settings, "OPENAI_API_KEY", "")
        )
        self.client = openai.AsyncOpenAI(api_key=getattr(settings, "OPENAI_API_KEY", "") or "sk-mock")
        self.model = settings.OPENAI_MODEL

    async def analyze(
        self,
        transcript: str,
        line_items: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        if not (transcript or "").strip():
            return {
                "mode": "no_transcript",
                "voice_claims": {},
                "document_state": {},
                "contradictions": [],
                "missing_evidence": [],
                "talking_points": [],
            }

        voice = extract_voice_claims(transcript)
        state = _document_state(line_items, documents)
        contradictions = detect_contradictions(voice, state)
        missing = _missing_evidence(voice, state)

        talking_points: list[dict] = []
        for c in contradictions:
            talking_points.append({
                "topic": c["type"],
                "severity": c.get("severity", "medium"),
                "point": c["description"],
            })
        for m in missing:
            talking_points.append({
                "topic": f"missing_{m['claim']}",
                "severity": "medium",
                "point": m["note"],
            })
        if not contradictions and not missing:
            talking_points.append({
                "topic": "no_contradictions",
                "severity": "info",
                "point": (
                    "Voice amendment is internally consistent with the shipment record; "
                    "annotate the customs audit trail with the verbatim transcript and proceed."
                ),
            })

        result: Dict[str, Any] = {
            "mode": "deterministic" if self.mock_mode else "gpt_attempted",
            "voice_claims": voice,
            "document_state": state,
            "contradictions": contradictions,
            "missing_evidence": missing,
            "talking_points": talking_points,
        }

        if self.mock_mode:
            return result

        try:
            import json
            prompt = (
                "You are a licensed customs broker preparing an amendment brief for a "
                "shipment about to be filed. Given the voice amendment + line items + "
                "trade documents, produce: (a) a 4-6 sentence customs-audit-ready "
                "narrative, (b) 3-5 talking points the broker can use during the "
                "client call. Return ONLY valid JSON: "
                "{\"narrative\": str, \"talking_points\":[str]}.\n\n"
                f"VOICE AMENDMENT:\n{transcript[:1500]}\n\n"
                f"LINE ITEMS:\n{json.dumps(line_items, default=str)[:1500]}\n\n"
                f"DOCUMENTS:\n{json.dumps(documents, default=str)[:1500]}\n"
            )
            resp = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                timeout=20,
                response_format={"type": "json_object"},
            )
            payload = json.loads(resp.choices[0].message.content or "{}")
            if payload.get("narrative"):
                result["narrative"] = payload["narrative"]
            for p in payload.get("talking_points", []) or []:
                if isinstance(p, str) and p.strip():
                    result["talking_points"].append({
                        "topic": "gpt", "severity": "info", "point": p.strip(),
                    })
            result["mode"] = "gpt"
        except Exception as e:
            result["error"] = str(e)[:200]
            result["mode"] = "fallback"
        return result
