import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.eligibility_engine import (
    EvaluateAllResponse,
    SchemeEvaluationResult,
    evaluate_all_schemes,
    load_scheme,
)
from app.scheme_catalogue import is_recommendable

STATUS_TIER = {
    "eligible": 1,
    "potentially_eligible": 2,
    "manual_verification_required": 3,
}

ACTION_REQUIRED_STATUSES = frozenset({
    "potentially_eligible",
    "manual_verification_required",
})

# Missing / ambiguous / verification codes must never receive positive weight,
# even if they are accidentally listed in recommendation_rules.json.
NON_POSITIVE_REASON_CODES = frozenset({
    "INCOME_INFORMATION_MISSING",
    "PURPOSE_AMBIGUOUS",
    "PURPOSE_INFORMATION_MISSING",
    "REQUESTED_AMOUNT_MISSING",
    "SCHEME_PARAMETER_VERIFICATION_REQUIRED",
    "PROJECT_COST_INFORMATION_MISSING",
    "COURSE_COST_INFORMATION_MISSING",
    "EDUCATION_STATUS_MISSING",
    "BENEFICIARY_CATEGORY_UNVERIFIED",
    "REQUESTED_AMOUNT_EXCEEDS_SCHEME_LIMIT",
    "REQUESTED_AMOUNT_EXCEEDS_DETERMINISTIC_FINANCING_LIMIT",
    "EDUCATION_REQUIREMENT_PENDING_VERIFICATION",
})


class ScoredScheme(BaseModel):
    scheme_id: str
    scheme_name: str
    eligibility_status: str
    status_tier: int
    recommendation_score: float
    scoring_reason_codes: List[str]
    eligibility_reason_codes: List[str]
    action_required_reason_codes: List[str]
    missing_information: List[str]
    verification_required_parameters: List[str]
    financial_assessment: Dict[str, Any]


class RankedRecommendations(BaseModel):
    top_recommendation: Optional[ScoredScheme]
    alternatives: List[ScoredScheme]


@dataclass
class RelevanceQuery:
    """Optional conversational relevance gate. Check Eligibility omits this."""
    assistance_type: str = "LOAN"
    domain: Optional[str] = None
    activity: Optional[str] = None
    amount_inr: Optional[float] = None


_LOAN_SCHEME_TYPES = frozenset({
    "TERM_LOAN", "MICRO_FINANCE", "BUSINESS_LOAN", "EDUCATION_LOAN",
})
_NON_LOAN_ASSISTANCE = frozenset({
    "SCHOLARSHIP", "OTHER_FINANCIAL_ASSISTANCE", "GRANT", "COACHING",
})
_NON_LOAN_SCHEME_TYPES = frozenset({
    "EDUCATION_SCHOLARSHIP", "OTHER_FINANCIAL_ASSISTANCE",
})
_EXCLUSIVE_NON_LOAN = (
    "scholarship", "coaching", "fellowship", "free coaching", "stipend",
    "interest subsidy",
)
_EXCLUSIVE_EDUCATION = ("educational loan", "education loan", "शैक्षिक ऋण")
_EXCLUSIVE_GREEN_ASSET = ("e-rickshaw", "e rickshaw", "solar", "clean-energy", "ई-रिक्शा", "सौर")
_EXPLICIT_AGRICULTURE = (
    "agriculture", "agricultural", "farming", "farm ", " farm",
    "kheti", "कृषि", "खेती", "dairy", "poultry", "paddy", "rice",
    "धान", "horticulture", "fishery", "allied agriculture", "crop",
)


def _explicit_agriculture_support(scheme: dict) -> bool:
    """True only if name/description actually mentions agriculture or allied activity.

    Classified domain/purpose tags are not enough: some NSFDC files were
    auto-tagged AGRICULTURE/FARMING while the scheme text is about other assets.
    """
    supported = {
        str(value).upper()
        for value in (
            list(scheme.get("supported_domains") or [])
            + list(scheme.get("supported_purposes") or [])
        )
    }
    if supported & {
        "AGRICULTURE", "LIVESTOCK", "FARMING", "CROP_CULTIVATION",
        "DAIRY", "POULTRY",
    }:
        return True
    desc = _description_text(scheme)
    if not desc:
        return False
    if any(marker in desc for marker in _EXCLUSIVE_GREEN_ASSET) and not any(
        w in desc for w in ("farm", "kheti", "कृषि", "agriculture", "dairy", "धान", "खेती")
    ):
        return False
    return any(marker in desc for marker in _EXPLICIT_AGRICULTURE)


def _description_text(scheme: dict) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    parts: list[str] = []
    for key in ("name", "shortDescription"):
        val = api.get(key)
        if isinstance(val, dict):
            parts.extend(str(v) for v in val.values())
        elif isinstance(val, str):
            parts.append(val)
    return " ".join(parts).lower()


def _scheme_text(scheme: dict) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    parts: list[str] = [
        str(scheme.get("scheme_id") or ""),
        str(scheme.get("scheme_type") or ""),
        str(scheme.get("domain") or ""),
        str(scheme.get("purpose") or ""),
        str(scheme.get("assistance_type") or ""),
    ]
    name = api.get("name")
    if isinstance(name, dict):
        parts.extend(str(v) for v in name.values())
    elif isinstance(name, str):
        parts.append(name)
    desc = api.get("shortDescription")
    if isinstance(desc, dict):
        parts.extend(str(v) for v in desc.values())
    elif isinstance(desc, str):
        parts.append(desc)
    return " ".join(parts).lower()


def _api_amount_bounds(scheme: dict) -> tuple[Optional[float], Optional[float]]:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    mn = api.get("minLoanAmount")
    mx = api.get("maxLoanAmount")
    try:
        mn_f = float(mn) if mn is not None else None
    except (TypeError, ValueError):
        mn_f = None
    try:
        mx_f = float(mx) if mx is not None else None
    except (TypeError, ValueError):
        mx_f = None
    return mn_f, mx_f


def _is_loan_product(scheme: dict) -> bool:
    assistance = str(scheme.get("assistance_type") or "").upper()
    scheme_type = str(scheme.get("scheme_type") or "").upper()
    if assistance == "LOAN" or scheme_type in _LOAN_SCHEME_TYPES:
        return True
    return False


def _has_sufficient_metadata(scheme: dict) -> bool:
    if not is_recommendable(scheme):
        return False
    assistance = str(scheme.get("assistance_type") or "").upper()
    scheme_type = str(scheme.get("scheme_type") or "").upper()
    domain = str(scheme.get("domain") or "").upper()
    mn, mx = _api_amount_bounds(scheme)
    if assistance in _NON_LOAN_ASSISTANCE and scheme_type in _NON_LOAN_SCHEME_TYPES:
        if domain in {"OTHER", "GENERAL", ""} and mn is None and mx is None:
            return False
        if not _is_loan_product(scheme):
            return False
    if not scheme.get("domain") and not assistance and mn is None:
        return False
    return True


def scheme_relevance_priority(scheme: dict, query: RelevanceQuery) -> int:
    """0 = not relevant enough to recommend. Higher is a better metadata match."""
    if not _has_sufficient_metadata(scheme):
        return 0
    text = _scheme_text(scheme)
    assistance = str(scheme.get("assistance_type") or "").upper()
    scheme_type = str(scheme.get("scheme_type") or "").upper()
    domain = str(scheme.get("domain") or "").upper()
    wanted = (query.assistance_type or "LOAN").upper()
    user_domain = (query.domain or "").upper()

    if wanted == "LOAN":
        if assistance in {"SCHOLARSHIP", "GRANT", "COACHING"}:
            return 0
        if scheme_type in {"EDUCATION_SCHOLARSHIP"}:
            return 0
        if any(marker in text for marker in _EXCLUSIVE_NON_LOAN):
            return 0
        if not _is_loan_product(scheme):
            return 0

    mn, mx = _api_amount_bounds(scheme)
    amount = query.amount_inr
    if amount is not None:
        if mx is not None and amount > mx:
            return 0
        if mn is not None and amount < mn:
            return 0

    if user_domain == "EDUCATION":
        if domain == "EDUCATION" and _is_loan_product(scheme) and scheme_type == "EDUCATION_LOAN":
            return 4
        if domain == "EDUCATION" and _is_loan_product(scheme):
            return 3
        return 0

    if user_domain == "AGRICULTURE":
        if domain == "EDUCATION" or any(marker in text for marker in _EXCLUSIVE_EDUCATION):
            return 0
        if not _explicit_agriculture_support(scheme):
            return 0
        if not _is_loan_product(scheme):
            return 0
        if domain == "AGRICULTURE":
            return 4
        return 3

    if user_domain == "BUSINESS":
        if domain in {"EDUCATION", "AGRICULTURE"}:
            return 0
        if scheme_type == "MICRO_FINANCE" and (amount is None or amount <= 125000):
            return 4
        if scheme_type == "TERM_LOAN" and (amount is None or amount > 125000):
            return 4
        if scheme_type in {"BUSINESS_LOAN", "TERM_LOAN", "MICRO_FINANCE"}:
            return 3
        if domain == "BUSINESS" and _is_loan_product(scheme):
            return 2
        return 0

    if _is_loan_product(scheme) and domain not in {"EDUCATION"}:
        return 1
    return 0


def apply_relevance_gate(
    eval_response: EvaluateAllResponse,
    query: Optional[RelevanceQuery],
) -> tuple[EvaluateAllResponse, Dict[str, int]]:
    if query is None:
        return eval_response, {}
    kept: List[SchemeEvaluationResult] = []
    priorities: Dict[str, int] = {}
    for res in eval_response.evaluated_schemes:
        try:
            scheme = load_scheme(res.scheme_id)
        except Exception:
            continue
        priority = scheme_relevance_priority(scheme, query)
        if priority <= 0:
            continue
        kept.append(res)
        priorities[res.scheme_id] = priority
    filtered = EvaluateAllResponse(
        user_profile_summary=eval_response.user_profile_summary,
        evaluated_schemes=kept,
        summary=eval_response.summary,
    )
    return filtered, priorities


def get_status_tier(status: str) -> int:
    return STATUS_TIER.get(status, 99)


@lru_cache(maxsize=1)
def load_recommendation_rules() -> List[dict]:
    rules_path = Path(__file__).parent.parent / "data" / "rules" / "recommendation_rules.json"
    if not rules_path.exists():
        return []
    with open(rules_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    # Handle both plain list format and {"rules": [...]} dict format
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("rules", [])
    return []


def _positive_scoring_rules(scheme_rules: List[dict]) -> List[dict]:
    positive = []
    for rule in scheme_rules:
        reason_code = rule.get("reason_code") or rule.get("eligibility_reason_code")
        weight = rule.get("weight", 0)
        if not reason_code or weight <= 0:
            continue
        if reason_code in NON_POSITIVE_REASON_CODES:
            continue
        positive.append({
            "reason_code": reason_code,
            "weight": weight,
            "scoring_reason_code": rule["scoring_reason_code"],
        })
    return positive


def _eligible_reason_codes(eval_res: SchemeEvaluationResult) -> set:
    return {check.reason_code for check in eval_res.checks if check.status == "eligible"}


def _action_required_reason_codes(eval_res: SchemeEvaluationResult) -> List[str]:
    seen = set()
    codes: List[str] = []
    for check in eval_res.checks:
        if check.status not in ACTION_REQUIRED_STATUSES:
            continue
        if check.reason_code in seen:
            continue
        seen.add(check.reason_code)
        codes.append(check.reason_code)
    return codes


def _calculate_recommendation_score(
    eval_res: SchemeEvaluationResult,
    scheme_rules: List[dict],
) -> tuple[float, List[str]]:
    positive_rules = _positive_scoring_rules(scheme_rules)
    eligible_codes = _eligible_reason_codes(eval_res)

    total_possible_weight = 0.0
    matched_weight = 0.0
    scoring_reason_codes: List[str] = []

    for rule in positive_rules:
        total_possible_weight += rule["weight"]
        if rule["reason_code"] in eligible_codes:
            matched_weight += rule["weight"]
            scoring_reason_codes.append(rule["scoring_reason_code"])

    if total_possible_weight <= 0:
        return 0.0, scoring_reason_codes

    return round(matched_weight / total_possible_weight, 4), scoring_reason_codes


def _score_scheme(eval_res: SchemeEvaluationResult, scheme_rules: List[dict]) -> ScoredScheme:
    rec_score, scoring_reason_codes = _calculate_recommendation_score(eval_res, scheme_rules)
    financial_assessment = eval_res.financial_assessment or {}
    verification_required = list(financial_assessment.get("verification_required_parameters", []))

    return ScoredScheme(
        scheme_id=eval_res.scheme_id,
        scheme_name=eval_res.scheme_name,
        eligibility_status=eval_res.eligibility_status,
        status_tier=get_status_tier(eval_res.eligibility_status),
        recommendation_score=rec_score,
        scoring_reason_codes=scoring_reason_codes,
        eligibility_reason_codes=list(eval_res.reason_codes),
        action_required_reason_codes=_action_required_reason_codes(eval_res),
        missing_information=list(eval_res.missing_information),
        verification_required_parameters=verification_required,
        financial_assessment=financial_assessment,
    )


def generate_recommendations(
    eval_response: EvaluateAllResponse,
    rules: Optional[List[dict]] = None,
    relevance: Optional[RelevanceQuery] = None,
) -> RankedRecommendations:
    """Rank schemes from eligibility-engine output. Does not recompute eligibility facts.

    When relevance is provided, incompatible or under-specified schemes are
    removed before score/UUID tie-breaking. Check Eligibility omits relevance.
    """
    gated, priorities = apply_relevance_gate(eval_response, relevance)
    loaded_rules = rules if rules is not None else load_recommendation_rules()
    rules_by_scheme = {r["scheme_id"]: r.get("scoring_rules", []) for r in loaded_rules}

    scored_schemes: List[ScoredScheme] = []
    for eval_res in gated.evaluated_schemes:
        if eval_res.eligibility_status == "not_eligible":
            continue
        scored_schemes.append(
            _score_scheme(eval_res, rules_by_scheme.get(eval_res.scheme_id, []))
        )

    scored_schemes.sort(
        key=lambda s: (
            s.status_tier,
            -s.recommendation_score,
            -priorities.get(s.scheme_id, 0),
            s.scheme_id,
        )
    )

    top = scored_schemes[0] if scored_schemes else None
    alternatives = scored_schemes[1:] if len(scored_schemes) > 1 else []

    return RankedRecommendations(
        top_recommendation=top,
        alternatives=alternatives,
    )


def recommend_from_profile(
    user_profile: Dict[str, Any],
    rules: Optional[List[dict]] = None,
    relevance: Optional[RelevanceQuery] = None,
    organization: Optional[str] = "NSFDC",
) -> RankedRecommendations:
    """User profile → eligibility engine → relevance gate → ranked recommendations."""
    return generate_recommendations(
        evaluate_all_schemes(user_profile, organization=organization),
        rules=rules,
        relevance=relevance,
    )
