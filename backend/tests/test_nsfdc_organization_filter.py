"""Targeted tests: optional NSFDC organization filter on evaluation/ranking."""

from app.eligibility_engine import evaluate_all_schemes, load_scheme
from app.recommendation_engine import generate_recommendations

FREE_COACHING_ID = "0070a49e-2e01-554a-8f33-e6ee5648877e"


def _ids(eval_response) -> set[str]:
    return {s.scheme_id for s in eval_response.evaluated_schemes}


def _org(scheme_id: str) -> str | None:
    return load_scheme(scheme_id).get("organization")


def _rank(user_profile: dict, organization: str | None = None):
    evaluated = evaluate_all_schemes(user_profile, organization=organization)
    return evaluated, generate_recommendations(evaluated)


def _assert_nsfdc_loan_candidates(evaluated, ranked):
    ids = _ids(evaluated)
    assert FREE_COACHING_ID not in ids
    assert ids
    assert all(_org(sid) == "NSFDC" for sid in ids)
    if ranked.top_recommendation:
        assert ranked.top_recommendation.scheme_id != FREE_COACHING_ID
        assert "free coaching" not in ranked.top_recommendation.scheme_name.lower()
        assert _org(ranked.top_recommendation.scheme_id) == "NSFDC"
    for alt in ranked.alternatives:
        assert alt.scheme_id != FREE_COACHING_ID
        assert _org(alt.scheme_id) == "NSFDC"


def test_unfiltered_evaluation_still_includes_non_nsfdc_catalogue():
    evaluated, _ = _rank(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        }
    )
    assert FREE_COACHING_ID in _ids(evaluated)


def test_nsfdc_filter_excludes_free_coaching():
    evaluated, ranked = _rank(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_agriculture_rice_loan_two_lakh_nsfdc_only():
    evaluated, ranked = _rank(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "language": "hi",
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_english_agriculture_loan_plus_amount():
    evaluated, ranked = _rank(
        {
            "purpose": "agriculture",
            "project_cost_inr": 200000,
            "language": "en",
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_hindi_agriculture_loan_plus_amount():
    evaluated, ranked = _rank(
        {
            "purpose": "DAIRY_FARMING",
            "project_cost_inr": 200000,
            "language": "hi",
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_education_loan_flow_nsfdc_only():
    evaluated, ranked = _rank(
        {
            "purpose": "engineering_education",
            "course_cost_inr": 1000000,
            "family_income_inr": 400000,
            "education_status": "admission_secured",
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_business_loan_flow_nsfdc_only():
    evaluated, ranked = _rank(
        {
            "purpose": "small_retail",
            "project_cost_inr": 100000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    _assert_nsfdc_loan_candidates(evaluated, ranked)


def test_free_coaching_cannot_be_top_recommendation_for_nsfdc_loan():
    _, ranked = _rank(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    assert ranked.top_recommendation is None or ranked.top_recommendation.scheme_id != FREE_COACHING_ID
    assert all(a.scheme_id != FREE_COACHING_ID for a in ranked.alternatives)
    if ranked.top_recommendation:
        assert "free coaching" not in ranked.top_recommendation.scheme_name.lower()
