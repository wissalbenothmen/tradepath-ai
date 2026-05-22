from __future__ import annotations
import re
import unicodedata
from typing import Any
from Levenshtein import distance as levenshtein_distance

# ---------------------------------------------------------------------------
# Scoring thresholds
# ---------------------------------------------------------------------------
CLEAR_THRESHOLD = 70
POTENTIAL_THRESHOLD = 90  # >= 90 → POSITIVE_MATCH, 70-89 → POTENTIAL_MATCH, <70 → CLEAR

# ---------------------------------------------------------------------------
# Phonetic helpers (simplified Soundex)
# ---------------------------------------------------------------------------
SOUNDEX_MAP = {c: d for d, chars in [
    ("1", "BFPV"), ("2", "CGJKQSXZ"), ("3", "DT"),
    ("4", "L"), ("5", "MN"), ("6", "R"),
] for c in chars}


def _soundex(name: str) -> str:
    name = name.upper().strip()
    if not name:
        return "0000"
    code = name[0]
    prev = SOUNDEX_MAP.get(name[0], "0")
    for ch in name[1:]:
        digit = SOUNDEX_MAP.get(ch, "0")
        if digit != "0" and digit != prev:
            code += digit
        prev = digit
    return (code + "000")[:4]


def _normalize(name: str) -> str:
    name = unicodedata.normalize("NFKD", name)
    name = name.encode("ascii", "ignore").decode()
    name = re.sub(r"[^a-zA-Z0-9 ]", " ", name)
    return " ".join(name.upper().split())


def _name_similarity_score(query: str, candidate: str) -> float:
    """Return 0-100 score combining Levenshtein + phonetic."""
    q = _normalize(query)
    c = _normalize(candidate)
    if not q or not c:
        return 0.0

    # Levenshtein edit distance (character level)
    max_len = max(len(q), len(c))
    edit_dist = levenshtein_distance(q, c)
    edit_score = max(0.0, 1.0 - edit_dist / max_len) * 100

    # Phonetic match on each token
    q_tokens = q.split()
    c_tokens = c.split()
    phonetic_hits = sum(
        1 for qt in q_tokens
        if any(_soundex(qt) == _soundex(ct) for ct in c_tokens)
    )
    phonetic_score = (phonetic_hits / max(len(q_tokens), 1)) * 100

    # Weighted combine: 70% edit, 30% phonetic
    return round(0.70 * edit_score + 0.30 * phonetic_score, 2)


# ---------------------------------------------------------------------------
# Simulated list entries (in production these come from Elasticsearch)
# ---------------------------------------------------------------------------
_MOCK_SDN_ENTRIES: list[dict[str, Any]] = [
    {"name": "KIM JONG UN", "list": "ofac_sdn", "country": "KP", "entity_type": "individual"},
    {"name": "VLADIMIR PUTIN", "list": "ofac_sdn", "country": "RU", "entity_type": "individual"},
    {"name": "HEZBOLLAH", "list": "ofac_sdn", "country": "LB", "entity_type": "organization"},
    {"name": "AL QAEDA", "list": "ofac_sdn", "country": "AF", "entity_type": "organization"},
    {"name": "IRAN AIR", "list": "ofac_consolidated", "country": "IR", "entity_type": "organization"},
    {"name": "ROSOBORONEXPORT", "list": "ofac_consolidated", "country": "RU", "entity_type": "organization"},
    {"name": "BEIJING SKYRIZON AVIATION", "list": "bis_entity_list", "country": "CN", "entity_type": "organization"},
    {"name": "HUAWEI TECHNOLOGIES", "list": "bis_entity_list", "country": "CN", "entity_type": "organization"},
]


async def screen_party(
    party_name: str,
    party_country: str | None = None,
    lists_to_check: list[str] | None = None,
) -> dict[str, Any]:
    """
    Screen a party name against denied party lists.
    Returns overall_result, highest_score, matches, lists_checked.
    """
    all_lists = [
        "ofac_sdn", "ofac_consolidated", "eu_consolidated",
        "un_security_council", "hm_treasury_uk",
        "bis_entity_list", "bis_denied_persons", "bis_unverified",
    ]
    lists_to_check = lists_to_check or all_lists

    matches: list[dict[str, Any]] = []
    highest_score = 0.0

    for entry in _MOCK_SDN_ENTRIES:
        if entry["list"] not in lists_to_check:
            continue
        score = _name_similarity_score(party_name, entry["name"])
        # Country boost: +5 if countries match
        if party_country and entry.get("country") == party_country.upper():
            score = min(100.0, score + 5.0)
        if score >= CLEAR_THRESHOLD:
            matches.append({
                "matched_name": entry["name"],
                "list": entry["list"],
                "country": entry.get("country"),
                "entity_type": entry.get("entity_type"),
                "score": score,
            })
            highest_score = max(highest_score, score)

    if highest_score >= POTENTIAL_THRESHOLD:
        overall_result = "positive_match"
    elif highest_score >= CLEAR_THRESHOLD:
        overall_result = "potential_match"
    else:
        overall_result = "clear"

    matches.sort(key=lambda m: m["score"], reverse=True)

    return {
        "overall_result": overall_result,
        "highest_score": highest_score,
        "matches": matches,
        "lists_checked": lists_to_check,
    }
