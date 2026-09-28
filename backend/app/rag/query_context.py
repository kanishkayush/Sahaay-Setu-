"""
Turn a user utterance plus conversation profile into a retrieval query.

Short follow-ups (amount, course, city, yes/no) merge into prior state
instead of replacing it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from app.rag.language_detect import DetectionResult, detect_language_and_intent
from app.rag.ontology import semantic_expansion
from app.schemas.chat import ChatProfile


_AGRI_ACTIVITIES = {
    "RICE_FARMING", "WHEAT_FARMING", "VEGETABLE_FARMING", "HORTICULTURE",
    "DAIRY_FARMING", "POULTRY", "FISHERY", "GOAT_REARING", "PIG_REARING",
    "CROP_FARMING", "FARMING", "AGRICULTURE",
}
_EDU_MARKERS = {
    "EDUCATION_LOAN", "EDUCATION", "BTECH", "BE", "MBBS", "BCA", "MCA", "MBA",
    "ITI", "DIPLOMA", "NURSING", "PHARMACY", "CLASS_10", "CLASS_12",
    "MEDICAL_GENERAL", "ENGINEERING_GENERAL", "ITI_DIPLOMA",
}


@dataclass
class RetrievalQuery:
    language: str
    intent: Optional[str]
    domain: Optional[str]
    assistance_type: str
    activity: Optional[str]
    purpose: Optional[str]
    organization_scope: str
    requested_amount: Optional[float]
    education_course: Optional[str]
    location: Optional[str]
    land_context: Optional[str]
    search_text: str
    utterance: str


_GENERIC_ACTIVITIES = {
    None, "", "FARMING", "AGRICULTURE", "GENERAL", "GENERAL_BUSINESS", "BUSINESS",
}


def _specific_activity(profile: Optional[ChatProfile], detection: DetectionResult) -> Optional[str]:
    if profile and profile.activity and str(profile.activity).upper() not in _GENERIC_ACTIVITIES:
        return profile.activity
    if detection.activity and str(detection.activity).upper() not in _GENERIC_ACTIVITIES:
        return detection.activity
    return None


def _domain_from_profile(profile: Optional[ChatProfile]) -> Optional[str]:
    if not profile:
        return None
    if profile.projectType == "EDUCATION":
        return "EDUCATION"
    if profile.projectType == "AGRICULTURE":
        return "AGRICULTURE"
    if profile.projectType in {
        "BUSINESS", "MICRO_ENTERPRISE", "MANUFACTURING",
        "SERVICES", "TRANSPORT_VEHICLE",
    }:
        return "BUSINESS"
    act = str(profile.activity or "").upper()
    if act in _AGRI_ACTIVITIES or "FARM" in act or "RICE" in act:
        return "AGRICULTURE"
    if act in _EDU_MARKERS:
        return "EDUCATION"
    if act in {"GENERAL_BUSINESS", "BUSINESS", "SMALL_RETAIL", "TAILORING", "SHOP"}:
        return "BUSINESS"
    return None


def _search_text(rq: RetrievalQuery, english_gloss: str | None = None) -> str:
    parts = [rq.utterance]
    if english_gloss and english_gloss.strip() != (rq.utterance or "").strip():
        parts.append(english_gloss)
    if rq.intent:
        parts.append(str(rq.intent).replace("_", " ").lower())
    if rq.domain:
        parts.append(rq.domain.lower())
    if rq.activity:
        parts.append(str(rq.activity).replace("_", " ").lower())
    if rq.assistance_type:
        parts.append(rq.assistance_type.lower())
    if rq.organization_scope:
        parts.append(rq.organization_scope)
    if rq.requested_amount is not None:
        parts.append(f"requested amount {int(rq.requested_amount)} rupees")
    if rq.education_course:
        parts.append(str(rq.education_course).replace("_", " "))
    if rq.location:
        parts.append(rq.location)
    if rq.land_context:
        parts.append(rq.land_context)
    parts.append(
        semantic_expansion(
            rq.domain,
            rq.activity or rq.intent or rq.purpose,
            rq.assistance_type,
        )
    )
    return " ".join(p for p in parts if p)


def build_retrieval_query(
    utterance: str,
    profile: Optional[ChatProfile] = None,
    detection: Optional[DetectionResult] = None,
    language: Optional[str] = None,
) -> RetrievalQuery:
    detection = detection or detect_language_and_intent(utterance)
    prior_domain = _domain_from_profile(profile)
    domain = detection.domain or prior_domain
    # Short follow-ups (amount, course, yes/no) must not wipe a known domain.
    # Full loan utterances such as "I need an education loan" are also short
    # (≤6 tokens) and MUST be allowed to switch domain.
    words = utterance.strip().split()
    strong_new_domain = bool(
        detection.intent in {"EDUCATION_LOAN", "AGRICULTURE", "BUSINESS"}
        and detection.domain
        and detection.domain != "OTHER"
        and not detection.is_low_info
        and detection.domain != prior_domain
    )
    if prior_domain and len(words) <= 6 and not strong_new_domain:
        domain = prior_domain

    activity = _specific_activity(profile, detection)
    if strong_new_domain:
        activity = (
            detection.activity
            if detection.activity and str(detection.activity).upper() not in _GENERIC_ACTIVITIES
            else None
        )
    education_course = None
    if profile and profile.activity:
        if prior_domain == "EDUCATION" or str(profile.activity).upper() in _EDU_MARKERS:
            education_course = profile.activity
    amount = None
    if profile and profile.estimatedProjectCost is not None:
        amount = float(profile.estimatedProjectCost)
    location = None
    if profile:
        bits = [b for b in (profile.districtCode, profile.stateCode, profile.pinCode) if b]
        location = ", ".join(bits) if bits else None
    land = None
    if profile and getattr(profile, "landHoldingAcres", None) is not None:
        land = f"{profile.landHoldingAcres} acres"

    assistance = detection.assistance_type or "LOAN"
    if detection.intent or prior_domain or (profile and profile.activity):
        assistance = "LOAN"
    if strong_new_domain:
        domain = detection.domain
        amount = None
        if detection.domain != "EDUCATION":
            education_course = None
    elif profile and profile.projectType == "EDUCATION":
        assistance = "LOAN"
        domain = "EDUCATION"

    intent = detection.intent
    if not intent and domain == "AGRICULTURE":
        intent = "AGRICULTURE"
    if not intent and domain == "EDUCATION":
        intent = "EDUCATION_LOAN"
    if not intent and domain == "BUSINESS":
        intent = "BUSINESS"

    rq = RetrievalQuery(
        language=language or detection.detected_language or "en",
        intent=intent,
        domain=domain,
        assistance_type=assistance,
        activity=activity,
        purpose=detection.purpose,
        organization_scope=detection.organization or "NSFDC",
        requested_amount=amount,
        education_course=education_course,
        location=location,
        land_context=land,
        search_text="",
        utterance=utterance,
    )
    return replace(
        rq,
        search_text=_search_text(rq, english_gloss=detection.translated_query_en),
    )
