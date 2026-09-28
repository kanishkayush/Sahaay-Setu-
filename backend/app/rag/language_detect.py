"""
app/rag/language_detect.py
──────────────────────────
Lightweight deterministic language detection and intent extraction.

Replaces the expensive LLM call for language detection in chat.py.
Handles Hindi (Devanagari), Roman Hindi / Hinglish, English, Marathi,
Bengali, Tamil, Telugu, and produces a structured intent when possible.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional


@dataclass
class DetectionResult:
    detected_language: str  # "en", "hi", "mr", "bn", "ta", "te"
    translated_query_en: str  # best-effort English gloss for retrieval
    is_low_info: bool
    intent: Optional[str]  # EDUCATION_LOAN, AGRICULTURE, BUSINESS, GENERAL_LOAN, None
    confidence: float
    organization: str
    domain: Optional[str]
    purpose: Optional[str]
    assistance_type: Optional[str]
    activity: Optional[str] = None  # specific activity only when the utterance names it


# ── Script detection ───────────────────────────────────────────────

_DEVANAGARI_RE = re.compile(r'[\u0900-\u097F]')
_BENGALI_RE = re.compile(r'[\u0980-\u09FF]')
_TAMIL_RE = re.compile(r'[\u0B80-\u0BFF]')
_TELUGU_RE = re.compile(r'[\u0C00-\u0C7F]')


def _script_language(text: str) -> Optional[str]:
    """Detect language from script (Devanagari, Bengali, Tamil, Telugu)."""
    deva = len(_DEVANAGARI_RE.findall(text))
    beng = len(_BENGALI_RE.findall(text))
    tamil = len(_TAMIL_RE.findall(text))
    telugu = len(_TELUGU_RE.findall(text))

    counts = {"hi": deva, "bn": beng, "ta": tamil, "te": telugu}
    best = max(counts, key=counts.get)
    if counts[best] >= 2:
        # Distinguish Hindi from Marathi heuristically
        if best == "hi":
            marathi_markers = {"आहे", "करा", "तुम्ही", "नाही", "आणि", "मध्ये"}
            if any(m in text for m in marathi_markers):
                return "mr"
        return best
    return None


# ── Roman Hindi detection ──────────────────────────────────────────

_ROMAN_HINDI_WORDS = frozenset({
    "mujhe", "chahiye", "chahie", "chaiye", "keliye", "ke", "liye",
    "karna", "hai", "hain", "kaise", "kya", "koi", "yojana",
    "padhai", "padhna", "padna", "shiksha", "vidya",
    "chawal", "kheti",
    "vyapar", "vyapaar", "bijnes", "karobar", "dukaan", "dukan",
    "paisa", "rupaye", "rupay", "paise",
    "rin", "karz", "lakh",
    "naya", "purana", "ghar", "gaon", "shahar",
    "aur", "ya", "lekin", "par", "se", "ka", "ki", "ko", "mein", "hum",
    "batao", "bataiye", "karo", "kijiye", "dijiye",
    "milega", "mil", "milta", "sakta", "sakte",
    "haan", "nahi", "nahin", "ji",
    "kitna", "kitne", "kitni", "kab", "kahan",
    "sarkari", "sarkar", "sarkaar",
    "rozgar", "rojgar", "naukri",
    "suvidha", "sahayata", "madad",
    "dhanda", "kaam", "udyog",
    "laghu", "lagat",
    "aajeevika", "jeevan", "jiwan",
})

def _is_roman_hindi(text: str) -> bool:
    """Returns True if the text is likely Roman Hindi / Hinglish."""
    words = text.lower().split()
    if len(words) == 1:
        return words[0] in _ROMAN_HINDI_WORDS
    if not words:
        return False
    hindi_count = sum(1 for w in words if w in _ROMAN_HINDI_WORDS)
    return hindi_count / len(words) >= 0.25


# ── Intent keywords ───────────────────────────────────────────────

_EDUCATION_KEYWORDS = frozenset({
    # English
    "education", "study", "studies", "college", "school", "university",
    "course", "degree", "btech", "b.tech", "mba", "masters", "phd",
    "student", "fees", "tuition", "graduation", "diploma",
    "engineering", "medical", "institute", "scholarship",
    "higher education", "bachelors", "admission", "mtech",
    "bca", "mca", "mbbs", "iti", "nursing", "pharmacy", "10th", "12th",
    "ba", "bsc", "bcom",
    # Hindi / Devanagari
    "पढ़ाई", "शिक्षा", "कॉलेज", "स्कूल", "विश्वविद्यालय",
    "कोर्स", "डिग्री", "छात्र", "फीस", "ट्यूशन",
    "बीटेक", "डिप्लोमा", "बीसीए", "एमबीए", "नर्सिंग", "फार्मेसी",
    # Roman Hindi
    "padhai", "paddhai", "padhna", "padna",
    "shiksha", "vidya", "college", "school",
})

_AGRICULTURE_KEYWORDS = frozenset({
    # English
    "agriculture", "farming", "farm", "dairy", "cattle", "livestock",
    "milk production", "goat", "goat rearing", "animal husbandry",
    "poultry", "fishery", "horticulture", "crop", "irrigation",
    "rice", "paddy", "chawal", "cultivation", "vegetable", "vegetables",
    # Hindi / Devanagari
    "खेती", "कृषि", "डेयरी", "पशुपालन", "पशुधन", "मछली", "चावल", "धान",
    "गाय", "भैंस", "बकरी", "मुर्गी",
    "फार्म", "फार्मिंग",
    "फसल", "खेत", "बागवानी", "सब्जी", "उगाने",
    # Roman Hindi
    "kheti", "khet", "krishi", "dairy", "pashupalan",
    "gaay", "bhains", "bakri", "murgi", "murga",
    "machhli", "machli",
    "fasal", "crop", "crops", "sabji", "bagwani", "ugane", "cultivation",
})

_BUSINESS_KEYWORDS = frozenset({
    # English
    "business", "startup", "enterprise", "company", "manufacturing",
    "shop", "store", "handicraft", "artisan", "weaving", "pottery",
    "transport", "rickshaw", "auto", "taxi", "vehicle",
    "trade", "trading", "vendor", "vending",
    "self employment", "self-employment", "tailoring", "salon", "catering",
    "repair", "workshop", "tools", "service business",
    "income generating", "commercial vehicle", "micro enterprise",
    # Hindi / Devanagari
    "व्यवसाय", "व्यापार", "बिज़नेस", "बिजनेस", "दुकान", "कारीगर",
    "हस्तशिल्प", "शिल्प", "परिवहन", "रिक्शा", "स्वरोजगार", "सिलाई",
    "सैलून", "मरम्मत", "औजार",
    "उद्यम", "निर्माण", "आय वाला", "व्यावसायिक वाहन", "सूक्ष्म",
    # Roman Hindi
    "vyapar", "vyapaar", "bijnes", "business",
    "dukaan", "dukan", "karobar", "dhanda",
    "handicraft", "karkhana",
    "rickshaw", "auto", "swarozgar", "silai", "salon", "catering", "repair",
    "income generating",
})

_LOAN_KEYWORDS = frozenset({
    "loan", "rin", "karz", "finance", "financing", "funding",
    "money", "paisa", "paise", "rupaye",
    "लोन", "ऋण", "कर्ज", "वित्त", "पैसा", "रुपये",
    "ருணம்", "கடன்", "రుణం",
    "sahayata", "madad", "help",
    "सहायता", "मदद",
})

_LOW_INFO_QUERIES = frozenset({
    "loan", "help", "scheme", "hi", "hello", "hey", "namaste",
    "ok", "yes", "no", "haan", "nahi", "ji",
    "लोन", "मदद", "योजना", "हेलो", "हाय",
    "ऋण", "কর্জ", "கடன்", "రుణం",
    "namaskar", "namaskaram",
})


def _extract_intent(text: str) -> Optional[str]:
    """Extract a loan intent from the query text."""
    text_lower = text.lower()
    words = set(re.split(r'\W+', text_lower))

    has_loan = bool(words & _LOAN_KEYWORDS) or any(kw in text_lower for kw in _LOAN_KEYWORDS)

    # Check specific intents
    def has_concept(concepts: frozenset[str]) -> bool:
        return bool(words & concepts) or any(
            keyword in text_lower
            for keyword in concepts
            if " " in keyword or any(ord(char) > 127 for char in keyword) or len(keyword) > 3
        )

    has_education = has_concept(_EDUCATION_KEYWORDS)
    has_agriculture = has_concept(_AGRICULTURE_KEYWORDS)
    has_business = has_concept(_BUSINESS_KEYWORDS)

    if has_education:
        return "EDUCATION_LOAN"
    if has_agriculture:
        return "AGRICULTURE"
    if has_business:
        return "BUSINESS"
    if has_loan:
        return "GENERAL_LOAN"
    return None


# ── English translation for retrieval ──────────────────────────────

_INTENT_TO_RETRIEVAL_QUERY = {
    "EDUCATION_LOAN": (
        "education educational loan studies higher education student loan "
        "college course fees पढ़ाई शिक्षा"
    ),
    "AGRICULTURE": "agriculture farming loan scheme",
    "BUSINESS": "business enterprise self-employment loan scheme",
    "GENERAL_LOAN": "loan financial assistance scheme",
}

# Specific activities are stored only when the utterance contains evidence.
# Generic "farming" / "खेती" must not become rice or dairy.
# "fasal/crop farming" is crop cultivation, not rice and not dairy.
_RICE_MARKERS = ("rice farming", "rice", "paddy", "chawal", "धान", "चावल")
_DAIRY_MARKERS = (
    "dairy farming", "dairy farm", "dairy", "livestock", "cattle",
    "डेयरी फार्मिंग", "डेयरी फार्म", "डेयरी", "दूध", "पशुपालन", "doodh",
)
_POULTRY_MARKERS = ("poultry", "murgi", "मुर्गी पालन", "मुर्गी")
_GOAT_MARKERS = ("goat farming", "goat", "bakri", "बकरी पालन", "बकरी")
_CROP_MARKERS = (
    "crop farming", "crop cultivation", "crop loan", "crops",
    "fasal ki kheti", "fasal kheti", "fasal",
    "फसल की खेती", "फसल",
)


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    for marker in markers:
        if not marker:
            continue
        if any(ord(ch) > 127 for ch in marker) or " " in marker:
            if marker in text:
                return True
        elif re.search(rf"(?<![a-z0-9]){re.escape(marker)}(?![a-z0-9])", text):
            return True
    return False


def extract_specific_activity(text: str) -> Optional[str]:
    """Return a specific activity code only when the user named it."""
    t = (text or "").lower()
    if not t.strip():
        return None
    if _has_marker(t, _RICE_MARKERS):
        return "RICE_FARMING"
    if _has_marker(t, _DAIRY_MARKERS):
        return "DAIRY_FARMING"
    if _has_marker(t, _POULTRY_MARKERS):
        return "POULTRY"
    if _has_marker(t, _GOAT_MARKERS):
        return "GOAT_REARING"
    if _has_marker(t, _CROP_MARKERS):
        return "CROP_FARMING"
    return None


def detect_language_and_intent(query: str) -> DetectionResult:
    """
    Fast deterministic language detection + intent extraction.

    Returns a DetectionResult with:
    - detected_language: 2-letter code
    - translated_query_en: English gloss for better retrieval
    - is_low_info: True if query is too generic to retrieve meaningfully
    - intent: structured intent string or None
    - confidence: 0.0-1.0
    """
    stripped = query.strip()
    stripped_lower = stripped.lower().strip()

    # Check for low-info queries
    is_low_info = stripped_lower in _LOW_INFO_QUERIES or len(stripped_lower) <= 2

    # Detect language from script
    lang = _script_language(stripped)

    if lang is None:
        # Check for Roman Hindi
        if _is_roman_hindi(stripped):
            lang = "hi"
        else:
            lang = "en"

    # Extract intent
    intent = _extract_intent(stripped)
    activity = extract_specific_activity(stripped)

    # Build a retrieval-friendly English translation from the utterance +
    # domain gloss. Do not inject rice/dairy unless the user named them.
    if intent and intent in _INTENT_TO_RETRIEVAL_QUERY:
        gloss = _INTENT_TO_RETRIEVAL_QUERY[intent]
        if activity:
            gloss = f"{activity.replace('_', ' ').lower()} {gloss}"
        if activity == "CROP_FARMING":
            gloss = f"{gloss} crop cultivation agriculture farming फसल खेती"
        translated = f"{stripped} {gloss}"
    else:
        translated = stripped  # Use original if no intent mapping

    confidence = 0.9 if lang != "en" or intent else 0.7

    domain = None
    purpose = "GENERAL"
    assistance_type = "LOAN" if intent != None else "OTHER"
    
    if intent == "EDUCATION_LOAN":
        domain = "EDUCATION"
        purpose = "HIGHER_EDUCATION"
        assistance_type = "LOAN"
    elif intent == "AGRICULTURE":
        domain = "AGRICULTURE"
        purpose = activity or "AGRICULTURE"
        assistance_type = "LOAN"
    elif intent == "BUSINESS":
        domain = "BUSINESS"
        purpose = "BUSINESS"
        assistance_type = "LOAN"
    elif intent == "GENERAL_LOAN":
        domain = "OTHER"
        assistance_type = "LOAN"

    return DetectionResult(
        detected_language=lang,
        translated_query_en=translated,
        is_low_info=is_low_info,
        intent=intent,
        confidence=confidence,
        organization="NSFDC",
        domain=domain,
        purpose=purpose,
        assistance_type=assistance_type,
        activity=activity,
    )
