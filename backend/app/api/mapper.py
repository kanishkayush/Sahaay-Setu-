"""
app/api/mapper.py
─────────────────
Translates between the frontend's Zod contract and the backend engines.

Rules:
  - Never recompute eligibility. Read from engine output only.
  - Never invent financial figures. Use deterministic financial_assessment.
  - Ambiguous project types stay ambiguous (purpose=None → engine returns
    potentially_eligible with PURPOSE_INFORMATION_MISSING).
  - score is 0–100 (frontend contract); converted from 0.0–1.0 only at this
    boundary. The internal engine is never changed.
  - source is "RULE_ENGINE" until an AI/RAG component is wired in.
    Returning "HYBRID" or "AI" before that is a misrepresentation.
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any

from app.api.scheme_loader import get_scheme, get_scheme_catalogue, get_scheme_by_internal_id
from app.eligibility_engine import SchemeEvaluationResult
from app.recommendation_engine import RankedRecommendations, ScoredScheme

# ---------------------------------------------------------------------------
# ProjectType → backend purpose.
# Only 1-to-1 verified mappings. Ambiguous types map to None so the engine
# returns PURPOSE_INFORMATION_MISSING rather than a fabricated purpose.
# ---------------------------------------------------------------------------

PROJECT_TYPE_TO_PURPOSE: dict[str, str | None] = {
    "AGRICULTURE": "agriculture",
    "ANIMAL_HUSBANDRY": None,       # could be dairy/poultry/fishery — engine keeps ambiguous
    "ARTISAN_CRAFT": "self_employment",
    "RETAIL_SHOP": "small_retail",
    "SERVICES": None,               # too broad — engine keeps ambiguous
    "SMALL_MANUFACTURING": "manufacturing",
    "TRANSPORT_VEHICLE": "transport",
    "EDUCATION": "engineering_education",  # triggers ELS path
    "OTHER": None,                  # deliberately ambiguous
}

# educationStatus → backend education_status
EDUCATION_STATUS_MAP: dict[str, str | None] = {
    "NONE": None,
    "PRIMARY": None,
    "SECONDARY": None,
    "HIGHER_SECONDARY": "admission_secured",
    "GRADUATE": "admission_secured",
    "POSTGRADUATE": "admission_secured",
    "VOCATIONAL": "admission_secured",
}

# ---------------------------------------------------------------------------
# Reason code → MatchReason kind + localized text
# ---------------------------------------------------------------------------

# Reason codes that map to a MATCH reason
_MATCH_CODES = frozenset({
    "PURPOSE_MATCH",
    "INCOME_WITHIN_LIMIT",
    "PROJECT_COST_WITHIN_LIMIT",
    "COURSE_COST_WITHIN_LIMIT",
    "REQUESTED_AMOUNT_WITHIN_LIMIT",
    "BENEFICIARY_CATEGORY_VERIFIED",
    "EDUCATION_STATUS_VERIFIED",
})

# Reason codes that map to a MISMATCH reason (blockers)
_MISMATCH_CODES = frozenset({
    "INCOME_EXCEEDS_LIMIT",
    "PURPOSE_NOT_SUPPORTED",
    "PROJECT_COST_EXCEEDS_LIMIT",
    "PROJECT_COST_BELOW_MINIMUM",
    "COURSE_COST_EXCEEDS_LIMIT",
    "COURSE_COST_BELOW_MINIMUM",
    "BENEFICIARY_CATEGORY_MISMATCH",
    "REQUESTED_AMOUNT_EXCEEDS_SCHEME_LIMIT",
    "REQUESTED_AMOUNT_EXCEEDS_DETERMINISTIC_FINANCING_LIMIT",
})

_REASON_TEXT: dict[str, dict[str, str]] = {
    "PURPOSE_MATCH": {
        "en": "Your activity matches this scheme's eligible purposes",
        "hi": "आपकी गतिविधि इस योजना के पात्र उद्देश्यों से मेल खाती है",
    },
    "INCOME_WITHIN_LIMIT": {
        "en": "Your family income is within the ₹5.00 lakh annual ceiling",
        "hi": "आपकी पारिवारिक आय ₹5.00 लाख की वार्षिक सीमा के भीतर है",
    },
    "PROJECT_COST_WITHIN_LIMIT": {
        "en": "Your project cost fits within this scheme's range",
        "hi": "आपकी परियोजना लागत इस योजना की सीमा के अंतर्गत है",
    },
    "COURSE_COST_WITHIN_LIMIT": {
        "en": "Your course cost is within the scheme limit",
        "hi": "आपकी पाठ्यक्रम लागत योजना की सीमा के भीतर है",
    },
    "REQUESTED_AMOUNT_WITHIN_LIMIT": {
        "en": "Your requested loan amount is within the scheme's maximum",
        "hi": "आपकी अनुरोधित ऋण राशि योजना की अधिकतम सीमा के भीतर है",
    },
    "BENEFICIARY_CATEGORY_VERIFIED": {
        "en": "You belong to the Scheduled Caste community (verified)",
        "hi": "आप अनुसूचित जाति समुदाय से हैं (सत्यापित)",
    },
    "EDUCATION_STATUS_VERIFIED": {
        "en": "Your education qualification meets the scheme requirement",
        "hi": "आपकी शैक्षिक योग्यता योजना की आवश्यकता को पूरा करती है",
    },
    "INCOME_EXCEEDS_LIMIT": {
        "en": "Annual family income exceeds the ₹5.00 lakh ceiling",
        "hi": "वार्षिक पारिवारिक आय ₹5.00 लाख की सीमा से अधिक है",
    },
    "PURPOSE_NOT_SUPPORTED": {
        "en": "Your stated purpose is not eligible under this scheme",
        "hi": "आपका उद्देश्य इस योजना के अंतर्गत पात्र नहीं है",
    },
    "PROJECT_COST_EXCEEDS_LIMIT": {
        "en": "Project cost is above this scheme's maximum",
        "hi": "परियोजना लागत इस योजना की अधिकतम सीमा से अधिक है",
    },
    "PROJECT_COST_BELOW_MINIMUM": {
        "en": "Project cost is below this scheme's minimum",
        "hi": "परियोजना लागत इस योजना की न्यूनतम सीमा से कम है",
    },
    "SCHEME_PARAMETER_VERIFICATION_REQUIRED": {
        "en": "Some scheme parameters need confirmation from the Channel Partner",
        "hi": "कुछ योजना मापदंडों की पुष्टि चैनल पार्टनर से करना आवश्यक है",
    },
    "INCOME_INFORMATION_MISSING": {
        "en": "Provide your annual family income to confirm eligibility",
        "hi": "पात्रता की पुष्टि के लिए अपनी वार्षिक पारिवारिक आय बताएं",
    },
    "PURPOSE_INFORMATION_MISSING": {
        "en": "Provide your business purpose to get a precise match",
        "hi": "सटीक मिलान के लिए अपना व्यवसाय उद्देश्य बताएं",
    },
    "PURPOSE_AMBIGUOUS": {
        "en": "Your purpose may qualify — confirm with a Channel Partner",
        "hi": "आपका उद्देश्य पात्र हो सकता है — चैनल पार्टनर से पुष्टि करें",
    },
    "REQUESTED_AMOUNT_EXCEEDS_SCHEME_LIMIT": {
        "en": "Your requested amount exceeds this scheme's loan ceiling",
        "hi": "आपकी अनुरोधित राशि इस योजना की ऋण सीमा से अधिक है",
    },
    "BENEFICIARY_CATEGORY_MISMATCH": {
        "en": "This scheme requires Scheduled Caste membership",
        "hi": "इस योजना के लिए अनुसूचित जाति सदस्यता आवश्यक है",
    },
    "EDUCATION_REQUIREMENT_PENDING_VERIFICATION": {
        "en": "Education qualification needs verification at the branch",
        "hi": "शैक्षिक योग्यता की शाखा पर जाँच आवश्यक है",
    },
    "BENEFICIARY_CATEGORY_UNVERIFIED": {
        "en": "SC/ST category could not be verified — confirm at the branch",
        "hi": "SC/ST श्रेणी सत्यापित नहीं हो सकी — शाखा पर पुष्टि करें",
    },
}

_DEFAULT_REASON_TEXT = {
    "en": "See scheme details for eligibility information",
    "hi": "पात्रता जानकारी के लिए योजना विवरण देखें",
}


def _reason_text(code: str) -> dict[str, str]:
    return _REASON_TEXT.get(code, _DEFAULT_REASON_TEXT)


def _reason_kind(code: str) -> str:
    if code in _MATCH_CODES:
        return "MATCH"
    if code in _MISMATCH_CODES:
        return "MISMATCH"
    return "INFO"


# ---------------------------------------------------------------------------
# Financial helpers — read from engine output, never recalculate.
# ---------------------------------------------------------------------------

def _eligible_loan_amount(scheme_id: str, financial_assessment: dict[str, Any]) -> int:
    """
    Use the engine's pre-computed financing figures. Never recalculate here.
    Falls back to the scheme JSON api.maxLoanAmount when the engine did not
    compute a project-specific figure (e.g. when project_cost_inr was not
    supplied).
    """
    max_possible = financial_assessment.get("maximum_possible_financing_inr")
    if max_possible is not None:
        return int(max_possible)

    # Engine had no project cost → return scheme JSON ceiling as upper bound.
    scheme = get_scheme_by_internal_id(scheme_id) or {}
    return scheme.get("maxLoanAmount", 0)

def _applicable_interest_rate(internal_scheme_id: str) -> float:
    """
    Read interestRateMinPct from the scheme JSON.
    Gender-differentiated rates (womenInterestRatePct) are only applicable
    for women-specific schemes. None of the three currently served verified
    schemes change rate by gender, so we read the floor rate.
    """
    scheme = get_scheme_by_internal_id(internal_scheme_id) or {}
    return scheme.get("interestRateMinPct", 0.0)


# ---------------------------------------------------------------------------
# Reason builders
# ---------------------------------------------------------------------------

def _build_reasons(scored: ScoredScheme) -> list[dict]:
    """
    Build MatchReason list from the engine's reason codes.
    MATCH/INFO codes from eligibility + action_required codes as INFO.
    """
    reasons: list[dict] = []
    for code in scored.eligibility_reason_codes:
        kind = _reason_kind(code)
        if kind in ("MATCH", "INFO"):
            reasons.append({"kind": kind, "text": _reason_text(code)})
    for code in scored.action_required_reason_codes:
        reasons.append({"kind": "INFO", "text": _reason_text(code)})
    return reasons


def _to_scheme_recommendation(scored: ScoredScheme) -> dict[str, Any]:
    scheme = get_scheme_by_internal_id(scored.scheme_id) or {}
    loan_amount = _eligible_loan_amount(scored.scheme_id, scored.financial_assessment)
    interest_rate = _applicable_interest_rate(scored.scheme_id)

    return {
        "scheme": scheme,
        # score: 0–100 (frontend contract). Converted from 0.0–1.0 only here.
        "score": math.floor(scored.recommendation_score * 100),
        "eligibleLoanAmount": loan_amount,
        "applicableInterestRatePct": interest_rate,
        "suggestedTenureMonths": scheme.get("maxTenureMonths", 0),
        "suggestedMoratoriumMonths": scheme.get("moratoriumMinMonths", 0),
        "reasons": _build_reasons(scored),
        "citations": scheme.get("citations", []),
        # source: "RULE_ENGINE" — deterministic eligibility + deterministic
        # scoring. No AI component is involved. Update to "HYBRID" only once
        # the RAG pipeline is wired into this response path.
        "source": "RULE_ENGINE",
    }


def _eval_result_to_near_miss(eval_result: SchemeEvaluationResult) -> dict[str, Any]:
    """Build a near-miss SchemeRecommendation from a not_eligible SchemeEvaluationResult."""
    scheme = get_scheme_by_internal_id(eval_result.scheme_id) or {}
    reasons: list[dict] = []
    for code in eval_result.reason_codes:
        kind = _reason_kind(code)
        reasons.append({"kind": kind, "text": _reason_text(code)})

    return {
        "scheme": scheme,
        "score": 0,
        "eligibleLoanAmount": scheme.get("maxLoanAmount", 0),
        "applicableInterestRatePct": _applicable_interest_rate(eval_result.scheme_id),
        "suggestedTenureMonths": scheme.get("maxTenureMonths", 0),
        "suggestedMoratoriumMonths": scheme.get("moratoriumMinMonths", 0),
        "reasons": reasons,
        "citations": scheme.get("citations", []),
        "source": "RULE_ENGINE",
    }


# ---------------------------------------------------------------------------
# Top-level response builder
# ---------------------------------------------------------------------------

def build_response(
    ranked: RankedRecommendations,
    not_eligible_schemes: list[SchemeEvaluationResult],
) -> dict[str, Any]:
    """
    Map RankedRecommendations → RecommendationResponse (frontend Zod contract).

    Only schemes that have an `api` block in their JSON are included in the
    response. Schemes without an `api` block are not yet ready to surface.

    near_misses: not_eligible schemes in the catalogue, sorted by fewest
    not_eligible check results (nearest miss = only one failing check).
    """
    recommendations = []
    if ranked.top_recommendation and get_scheme_by_internal_id(ranked.top_recommendation.scheme_id):
        recommendations.append(_to_scheme_recommendation(ranked.top_recommendation))
    for alt in ranked.alternatives:
        if get_scheme_by_internal_id(alt.scheme_id):
            recommendations.append(_to_scheme_recommendation(alt))

    near_miss_candidates = [
        s for s in not_eligible_schemes if get_scheme_by_internal_id(s.scheme_id)
    ]
    near_miss_candidates.sort(
        key=lambda s: sum(1 for c in s.checks if c.status == "not_eligible")
    )
    near_misses = [_eval_result_to_near_miss(s) for s in near_miss_candidates[:3]]

    return {
        "recommendations": recommendations,
        "nearMisses": near_misses,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "offline": False,
    }
