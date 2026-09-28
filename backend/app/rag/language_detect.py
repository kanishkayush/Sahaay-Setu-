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
    if intent is None:
        from app.rag.scheme_advisor import COMPARE, EXPLAIN, OPTIONS, detect_adviser_mode
        mode, named = detect_adviser_mode(stripped)
        if mode in {OPTIONS, EXPLAIN, COMPARE}:
            intent = "EDUCATION_LOAN" if named == ["nsfdc-education"] else "GENERAL_LOAN"
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


# ── Conversation language (session-sticky) ─────────────────────────
#
# Token language ("BTech" is English letters) is not conversation language.
# Short entity/value replies inherit the established session language.

_EN_SWITCH_RE = re.compile(
    r"(?:please\s+)?(?:can\s+you\s+)?explain\s+(?:this|it)\s+in\s+english"
    r"|in\s+english\s+please"
    r"|switch\s+to\s+english"
    r"|reply\s+in\s+english"
    r"|answer\s+in\s+english"
    r"|respond\s+in\s+english"
    r"|please\s+answer\s+in\s+english"
    r"|speak\s+(?:in\s+)?english"
    r"|english\s+me(?:n|in)?\s+batao"
    r"|english\s+में\s+बताओ"
    r"|अब\s+english",
    re.IGNORECASE,
)
_HI_SWITCH_RE = re.compile(
    r"(?:हिंदी|हिन्दी)\s*में\s*(?:बताओ|समझाओ|बोलो|जवाब)"
    r"|hindi\s+me(?:n|in)?\s+samjhao"
    r"|explain\s+(?:this|it)\s+in\s+hindi"
    r"|switch\s+to\s+hindi"
    r"|in\s+hindi\s+please"
    r"|reply\s+in\s+hindi",
    re.IGNORECASE,
)
_AMOUNT_UTTERANCE_RE = re.compile(
    r"^\s*(?:₹|rs\.?|inr)?\s*\d[\d,]*\s*"
    r"(?:lakh|lac|लाख|thousand|hazar|हजार|k|rupees?|rupaye|रूपये|₹)?\s*$",
    re.IGNORECASE,
)
_EN_FUNCTION_WORDS = frozenset({
    "i", "we", "you", "me", "my", "please", "need", "want", "can", "could",
    "would", "explain", "tell", "what", "how", "where", "why", "the", "a",
    "an", "for", "this", "that", "is", "am", "are", "do", "does", "did",
})
_SHORT_ENTITY_WORDS = frozenset({
    "btech", "b.tech", "mbbs", "iti", "mba", "mtech", "bca", "mca", "be",
    "bsc", "bcom", "diploma", "nursing", "pharmacy",
    "jaipur", "delhi", "mumbai", "kolkata", "chennai", "hyderabad",
    "bengaluru", "bangalore", "pune", "lucknow", "patna", "ahmedabad",
    "lakh", "lac", "rupees", "rupee",
})
_ROMAN_HINDI_LANGUAGE_WORDS = _ROMAN_HINDI_WORDS - {
    "lakh", "rupaye", "rupay", "paise", "paisa",
}


def _explicit_switch_to_english(text: str) -> bool:
    return bool(_EN_SWITCH_RE.search(text or ""))


def _explicit_switch_to_hindi(text: str) -> bool:
    return bool(_HI_SWITCH_RE.search(text or ""))


def _is_slot_value_utterance(text: str) -> bool:
    """Amount/income/course slot answers should inherit conversation language."""
    stripped = (text or "").strip()
    if not stripped or _explicit_switch_to_english(stripped) or _explicit_switch_to_hindi(stripped):
        return False
    if len(stripped.split()) > 14:
        return False
    if _AMOUNT_UTTERANCE_RE.match(stripped):
        return True
    return bool(re.search(
        r"(?:family\s+income|annual\s+income|income\s+is|आय|"
        r"(?:\d[\d,]*|[a-zA-Z]+)\s*(?:lakh|lac|लाख))",
        stripped,
        re.IGNORECASE,
    ))


def _is_amount_or_short_entity(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if _AMOUNT_UTTERANCE_RE.match(stripped):
        return True
    if _DEVANAGARI_RE.search(stripped) or _BENGALI_RE.search(stripped) or _TAMIL_RE.search(stripped) or _TELUGU_RE.search(stripped):
        return False
    words = re.findall(r"[a-zA-Z0-9.]+", stripped.lower())
    if not words or len(words) > 4:
        return False
    if any(w in _ROMAN_HINDI_LANGUAGE_WORDS for w in words):
        return False
    if sum(1 for w in words if w in _EN_FUNCTION_WORDS) >= 2:
        return False
    if len(words) <= 3:
        return True
    return all(w in _SHORT_ENTITY_WORDS or w.isdigit() or len(w) <= 4 for w in words)


def _is_roman_hindi_sentence(text: str) -> bool:
    words = re.findall(r"[a-zA-Z]+", (text or "").lower())
    if not words:
        return False
    hits = sum(1 for w in words if w in _ROMAN_HINDI_LANGUAGE_WORDS)
    if len(words) == 1:
        return words[0] in _ROMAN_HINDI_LANGUAGE_WORDS
    return hits >= 2 or hits / len(words) >= 0.25


def _is_clear_english_utterance(text: str) -> bool:
    if _DEVANAGARI_RE.search(text or ""):
        return False
    if _is_roman_hindi_sentence(text):
        return False
    words = re.findall(r"[a-zA-Z']+", (text or "").lower())
    if len(words) < 3:
        return False
    function_hits = sum(1 for w in words if w in _EN_FUNCTION_WORDS)
    return len(words) >= 5 or function_hits >= 2


def resolve_conversation_language(
    query: str,
    prior: Optional[str] = None,
    app_hint: Optional[str] = None,
) -> str:
    """Choose the conversation language for this turn.

    Distinguishes the language of the current token from the language of the
    conversation. Short names, courses, cities, and amounts inherit `prior`.
    """
    text = (query or "").strip()
    prior_lang = (prior or "").strip().lower() or None
    hint = (app_hint or "").strip().lower() or None

    if not text:
        return prior_lang or hint or "en"
    if _explicit_switch_to_english(text):
        return "en"
    if _explicit_switch_to_hindi(text):
        return "hi"

    script = _script_language(text)
    if script:
        return script
    if _is_amount_or_short_entity(text):
        return prior_lang or hint or "en"
    if _is_roman_hindi_sentence(text):
        return "hi"
    if prior_lang and _is_slot_value_utterance(text):
        return prior_lang
    if _is_clear_english_utterance(text):
        return "en"

    detection = detect_language_and_intent(text)
    if prior_lang and detection.detected_language != prior_lang and (
        detection.is_low_info or len(text.split()) <= 4
    ):
        return prior_lang
    return detection.detected_language or prior_lang or hint or "en"
