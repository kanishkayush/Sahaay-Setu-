import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.eligibility_engine import (
    EvaluateAllResponse,
    SchemeEvaluationResult,
    evaluate_all_schemes,
)

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


def get_status_tier(status: str) -> int:
    return STATUS_TIER.get(status, 99)


@lru_cache(maxsize=1)
def load_recommendation_rules() -> List[dict]:
    rules_path = Path(__file__).parent.parent / "data" / "rules" / "recommendation_rules.json"
    with open(rules_path, "r", encoding="utf-8") as f:
        return json.load(f)


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
) -> RankedRecommendations:
    """Rank schemes from eligibility-engine output. Does not recompute eligibility facts.

    Ranking:
      1. Drop not_eligible schemes
      2. Compute normalized recommendation_score from positive reason-code weights
      3. Assign status_tier (eligible=1, potentially_eligible=2, manual_verification_required=3)
      4. Sort by status_tier ASC, recommendation_score DESC, scheme_id ASC
      5. First result is top_recommendation; the rest are alternatives
    """
    loaded_rules = rules if rules is not None else load_recommendation_rules()
    rules_by_scheme = {r["scheme_id"]: r.get("scoring_rules", []) for r in loaded_rules}

    scored_schemes: List[ScoredScheme] = []
    for eval_res in eval_response.evaluated_schemes:
        if eval_res.eligibility_status == "not_eligible":
            continue
        scored_schemes.append(
            _score_scheme(eval_res, rules_by_scheme.get(eval_res.scheme_id, []))
        )

    scored_schemes.sort(
        key=lambda s: (s.status_tier, -s.recommendation_score, s.scheme_id)
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
) -> RankedRecommendations:
    """User profile → eligibility engine → ranked recommendations."""
    return generate_recommendations(evaluate_all_schemes(user_profile), rules=rules)
