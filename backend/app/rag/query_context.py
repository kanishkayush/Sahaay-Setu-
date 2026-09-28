"""
Turn a user utterance plus conversation profile into a retrieval query.

Short follow-ups (amount, course, city, yes/no) merge into prior state
instead of replacing it.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Optional

from app.rag.language_detect import DetectionResult, detect_language_and_intent
from app.schemas.chat import ChatProfile


_AGRI_ACTIVITIES = {
    "RICE_FARMING", "WHEAT_FARMING", "VEGETABLE_FARMING", "HORTICULTURE",
    "DAIRY_FARMING", "POULTRY", "FISHERY", "GOAT_REARING", "PIG_REARING",
    "FARMING", "AGRICULTURE",
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


def _domain_from_profile(profile: Optional[ChatProfile]) -> Optional[str]:
    if not profile:
        return None
    if profile.projectType == "EDUCATION":
        return "EDUCATION"
    act = str(profile.activity or "").upper()
    if act in _AGRI_ACTIVITIES or "FARM" in act or "RICE" in act:
        return "AGRICULTURE"
    if act in _EDU_MARKERS:
        return "EDUCATION"
    if act in {"GENERAL_BUSINESS", "BUSINESS", "SMALL_RETAIL", "TAILORING", "SHOP"}:
        return "BUSINESS"
    return None


def _search_text(rq: RetrievalQuery) -> str:
    parts = [rq.utterance]
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
    if rq.domain == "AGRICULTURE":
        parts.append("agriculture farming self-employment loan")
    elif rq.domain == "EDUCATION":
        parts.append("education loan professional technical course")
    elif rq.domain == "BUSINESS":
        parts.append("business self-employment loan")
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
    # Short contextual answers must not wipe a known domain.
    words = utterance.strip().split()
    if prior_domain and len(words) <= 6:
        domain = prior_domain

    activity = None
    education_course = None
    if profile and profile.activity:
        activity = profile.activity
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
    if profile and profile.projectType == "EDUCATION":
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
    return replace(rq, search_text=_search_text(rq))
