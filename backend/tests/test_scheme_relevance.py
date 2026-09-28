"""Relevance gate: NSFDC loan path must not rank by UUID among empty-parameter schemes."""

from typing import Optional

from app.eligibility_engine import evaluate_all_schemes, load_scheme
from app.recommendation_engine import RelevanceQuery, generate_recommendations, scheme_relevance_priority

FREE_COACHING_ID = "0070a49e-2e01-554a-8f33-e6ee5648877e"
NSFDC_SHELL_ID = "eda53729-9585-58fc-8901-fd767c15ea83"


def _rank(profile: dict, domain: str, amount: Optional[float], organization: Optional[str] = "NSFDC"):
    evaluated = evaluate_all_schemes(profile, organization=organization)
    ranked = generate_recommendations(
        evaluated,
        relevance=RelevanceQuery(
            assistance_type="LOAN",
            domain=domain,
            amount_inr=amount,
        ),
    )
    return evaluated, ranked


def test_agriculture_two_lakh_does_not_force_term_loan():
    _, ranked = _rank(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        domain="AGRICULTURE",
        amount=200000,
    )
    assert ranked.top_recommendation is None
    assert all(a.scheme_id != FREE_COACHING_ID for a in ranked.alternatives)
    assert all("coach" not in a.scheme_name.lower() for a in ranked.alternatives)
    assert all("scholarship" not in a.scheme_name.lower() for a in ranked.alternatives)


def test_term_loan_is_not_agriculture_relevant_from_catalogue():
    scheme = load_scheme("nsfdc-term-loan")
    assert scheme.get("domain") == "BUSINESS"
    assert scheme.get("purpose") == "BUSINESS"
    desc = ((scheme.get("api") or {}).get("shortDescription") or {}).get("en", "").lower()
    assert "manufacturing" in desc or "transport" in desc or "service" in desc
    assert "agricultur" not in desc and "farm" not in desc
    priority = scheme_relevance_priority(
        scheme,
        RelevanceQuery(assistance_type="LOAN", domain="AGRICULTURE", amount_inr=200000),
    )
    assert priority == 0
    biz = scheme_relevance_priority(
        scheme,
        RelevanceQuery(assistance_type="LOAN", domain="BUSINESS", amount_inr=200000),
    )
    assert biz > 0


def test_education_loan_selects_educational_loan_not_scholarship():
    _, ranked = _rank(
        {
            "purpose": "engineering_education",
            "course_cost_inr": 500000,
            "family_income_inr": 400000,
            "education_status": "admission_secured",
            "beneficiary_category_verified": True,
        },
        domain="EDUCATION",
        amount=500000,
    )
    assert ranked.top_recommendation is not None
    top = ranked.top_recommendation
    assert top.scheme_id == "nsfdc-education"
    assert "scholarship" not in top.scheme_name.lower()
    assert "coach" not in top.scheme_name.lower()
    scheme = load_scheme(top.scheme_id)
    assert scheme.get("scheme_type") == "EDUCATION_LOAN"
    assert scheme.get("assistance_type") == "LOAN"


def test_business_two_lakh_selects_term_loan():
    _, ranked = _rank(
        {
            "purpose": "small_retail",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        domain="BUSINESS",
        amount=200000,
    )
    assert ranked.top_recommendation is not None
    assert ranked.top_recommendation.scheme_id == "nsfdc-term-loan"


def test_under_specified_nsfdc_shell_cannot_win_agriculture():
    scheme = load_scheme(NSFDC_SHELL_ID)
    priority = scheme_relevance_priority(
        scheme,
        RelevanceQuery(assistance_type="LOAN", domain="AGRICULTURE", amount_inr=200000),
    )
    assert priority == 0


def test_unfiltered_evaluation_still_includes_non_nsfdc():
    evaluated = evaluate_all_schemes(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        }
    )
    ids = {s.scheme_id for s in evaluated.evaluated_schemes}
    assert FREE_COACHING_ID in ids
