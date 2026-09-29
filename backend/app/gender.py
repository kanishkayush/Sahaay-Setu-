"""Canonical gender representation for RAG, eligibility, and ranking.

Stored value is FEMALE | MALE | OTHER — the existing ApplicantProfile enum.
Utterances such as "woman" / "महिला" normalize to FEMALE.
Missing catalogue gender is UNKNOWN, never MATCH or MISMATCH.
"""

from __future__ import annotations

import re
from typing import Any, Optional

CANONICAL_FEMALE = "FEMALE"
CANONICAL_MALE = "MALE"
CANONICAL_OTHER = "OTHER"
CANONICAL_ANY = "ANY"

FIT_MATCH = "MATCH"
FIT_RELATED = "RELATED"
FIT_UNKNOWN = "UNKNOWN"
FIT_MISMATCH = "MISMATCH"

_FEMALE_WORDS = frozenset({
    "woman", "women", "female", "lady", "ladies",
    "mahila", "mahilae", "mahilao", "mahilaon", "mahilaonke",
    "aurat", "auratein", "stree", "stree",
})
_FEMALE_PHRASES = (
    "i am a woman",
    "i'm a woman",
    "im a woman",
    "i am woman",
    "for women",
    "for a woman",
    "women beneficiaries",
    "women beneficiary",
    "women entrepreneurs",
    "women entrepreneur",
    "women applicants",
    "scheme for women",
    "schemes for women",
    "महिलाओं के लिए",
    "महिला के लिए",
    "मैं एक महिला",
    "मै एक महिला",
    "महिला हूँ",
    "महिला हूं",
    "main ek mahila",
    "main mahila",
    "women ke liye",
    "mahilaon ke liye",
    "mahila ke liye",
)
_FEMALE_DEVANAGARI = ("महिला", "महिलाओं", "स्त्री", "औरत")
_MALE_WORDS = frozenset({"man", "men", "male", "gentleman"})
_MALE_PHRASES = ("i am a man", "i'm a man", "for men", "मैं एक पुरुष", "पुरुषों के लिए")
_MALE_DEVANAGARI = ("पुरुष", "पुरुषों")

_FEMALE_ALIASES = {
    "FEMALE", "WOMAN", "WOMEN", "F", "LADY", "GIRL",
    "महिला", "महिलाओं",
}
_MALE_ALIASES = {"MALE", "MAN", "MEN", "M", "पुरुष", "पुरुषों"}
_OTHER_ALIASES = {"OTHER", "NON_BINARY", "NONBINARY", "NB"}
_ANY_ALIASES = {"ANY", "ALL", "BOTH", "UNRESTRICTED"}


def normalize_gender(value: Any) -> Optional[str]:
    """Map any supported label onto FEMALE | MALE | OTHER | ANY."""
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return None
    key = raw.upper().replace("-", "_").replace(" ", "_")
    if key in _FEMALE_ALIASES or raw.lower() in _FEMALE_WORDS:
        return CANONICAL_FEMALE
    if key in _MALE_ALIASES or raw.lower() in _MALE_WORDS:
        return CANONICAL_MALE
    if key in _OTHER_ALIASES:
        return CANONICAL_OTHER
    if key in _ANY_ALIASES:
        return CANONICAL_ANY
    if any(tok in raw for tok in _FEMALE_DEVANAGARI):
        return CANONICAL_FEMALE
    if any(tok in raw for tok in _MALE_DEVANAGARI):
        return CANONICAL_MALE
    return None


def extract_gender(text: str) -> Optional[str]:
    """Return canonical gender when the utterance names it. Never infers from purpose."""
    original = text or ""
    lowered = original.lower()
    if not lowered.strip():
        return None
    if any(phrase in lowered or phrase in original for phrase in _FEMALE_PHRASES):
        return CANONICAL_FEMALE
    if any(tok in original for tok in _FEMALE_DEVANAGARI):
        return CANONICAL_FEMALE
    if any(phrase in lowered or phrase in original for phrase in _MALE_PHRASES):
        return CANONICAL_MALE
    if any(tok in original for tok in _MALE_DEVANAGARI):
        return CANONICAL_MALE
    words = set(re.split(r"\W+", lowered))
    if words & _FEMALE_WORDS:
        return CANONICAL_FEMALE
    if words & _MALE_WORDS:
        return CANONICAL_MALE
    return None


def is_gender_discovery_query(text: str, intent: Optional[str] = None) -> bool:
    """True when the user is asking for women/men schemes, not filling a gender slot on another purpose."""
    if extract_gender(text) is None:
        return False
    if intent in {"EDUCATION_LOAN", "AGRICULTURE", "BUSINESS"}:
        return False
    blob = f"{text or ''} {intent or ''}".lower()
    discovery_markers = (
        "scheme", "schemes", "yojana", "yojanaen", "योजना", "योजनाएं", "योजनाएँ",
        "options", "available", "apply", "kaunsi", "कौन", "कौनसी", "चाहिए", "chahiye",
        "loan", "लोन",
    )
    return any(marker in blob or marker in (text or "") for marker in discovery_markers)


def scheme_eligible_gender(scheme: dict) -> Optional[str]:
    """Catalogue gender restriction. None means the record has no gender field."""
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    raw = api.get("eligibleGender")
    if raw is None:
        raw = scheme.get("eligibleGender")
    normalized = normalize_gender(raw)
    if normalized:
        return normalized
    for rule in api.get("eligibilityRules") or []:
        if str(rule.get("field") or "").lower() != "gender":
            continue
        return normalize_gender(rule.get("value"))
    return None


def gender_fit_role(scheme: dict, user_gender: Optional[str]) -> str:
    """MATCH / RELATED / UNKNOWN / MISMATCH from catalogue gender metadata only."""
    user = normalize_gender(user_gender)
    if user in {CANONICAL_ANY, None}:
        return FIT_UNKNOWN
    if user == CANONICAL_OTHER:
        restriction = scheme_eligible_gender(scheme)
        if restriction in {CANONICAL_FEMALE, CANONICAL_MALE}:
            return FIT_MISMATCH
        return FIT_UNKNOWN
    restriction = scheme_eligible_gender(scheme)
    if restriction is None or restriction == CANONICAL_ANY:
        return FIT_UNKNOWN
    if restriction == user:
        return FIT_MATCH
    if restriction in {CANONICAL_FEMALE, CANONICAL_MALE} and user in {CANONICAL_FEMALE, CANONICAL_MALE}:
        return FIT_MISMATCH
    return FIT_UNKNOWN
