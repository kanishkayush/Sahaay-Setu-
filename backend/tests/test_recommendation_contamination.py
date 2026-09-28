"""Profile recommendations must not leak Free Coaching or cross-domain schemes."""

from fastapi.testclient import TestClient

from app.eligibility_engine import evaluate_all_schemes
from app.main import app
from app.profile_normalization import relevance_from_project_type, tri_bool
from app.recommendation_engine import generate_recommendations

FREE_COACHING_ID = "0070a49e-2e01-554a-8f33-e6ee5648877e"
client = TestClient(app)


def _recommend(project_type: str, cost: int = 2000000, income: int = 250000, education="VOCATIONAL"):
    return client.post(
        "/v1/recommendations",
        json={
            "language": "en",
            "profile": {
                "projectType": project_type,
                "estimatedProjectCost": cost,
                "annualFamilyIncome": income,
                "educationStatus": education,
                "gender": "FEMALE",
            },
        },
    )


def _ids(payload: dict) -> set[str]:
    recs = payload.get("recommendations") or []
    return {r.get("scheme", {}).get("id") or r.get("scheme", {}).get("schemeId") for r in recs}


def test_dairy_livestock_does_not_recommend_free_coaching():
    res = _recommend("ANIMAL_HUSBANDRY")
    assert res.status_code == 200
    body = res.json()
    names = " ".join(
        str((r.get("scheme") or {}).get("name") or "") + str((r.get("scheme") or {}).get("id") or "")
        for r in body.get("recommendations") or []
    ).lower()
    assert "free coaching" not in names
    assert FREE_COACHING_ID not in names
    for rec in body.get("recommendations") or []:
        scheme = rec.get("scheme") or {}
        assert "coach" not in str(scheme.get("name", {})).lower()
        assert "scholarship" not in str(scheme.get("name", {})).lower()


def test_agriculture_does_not_recommend_education_or_coaching():
    res = _recommend("AGRICULTURE")
    assert res.status_code == 200
    blob = str(res.json()).lower()
    assert "free coaching" not in blob or not any(
        (r.get("scheme") or {}).get("id") == FREE_COACHING_ID
        for r in res.json().get("recommendations") or []
    )
    assert all(
        "coach" not in str((r.get("scheme") or {}).get("name", "")).lower()
        for r in res.json().get("recommendations") or []
    )


def test_education_does_not_recommend_agriculture():
    res = _recommend("EDUCATION", cost=400000, education="GRADUATE")
    assert res.status_code == 200
    recs = res.json().get("recommendations") or []
    assert recs
    top = recs[0]["scheme"]
    sid = top.get("id") or top.get("schemeId")
    assert sid == "nsfdc-education" or "education" in str(top.get("name", "")).lower()


def test_business_does_not_recommend_scholarship_or_coaching():
    res = _recommend("RETAIL_SHOP", cost=200000)
    assert res.status_code == 200
    recs = res.json().get("recommendations") or []
    assert recs
    for rec in recs:
        scheme = rec.get("scheme") or {}
        name = str(scheme.get("name", "")).lower()
        sid = scheme.get("id")
        assert "scholarship" not in name
        assert "coaching" not in name
        if sid:
            from app.eligibility_engine import load_scheme
            raw = load_scheme(sid)
            assert raw.get("organization") == "NSFDC"
            assert raw.get("domain") != "AGRICULTURE"
            assert raw.get("domain") != "EDUCATION"


def test_tri_bool_unknown_is_not_false():
    assert tri_bool(None) is None
    assert tri_bool(True) is True
    assert tri_bool(False) is False


def test_engine_relevance_gate_dairy_profile():
    relevance = relevance_from_project_type("ANIMAL_HUSBANDRY", amount_inr=2000000)
    evaluated = evaluate_all_schemes(
        {
            "purpose": None,
            "project_cost_inr": 2000000,
            "family_income_inr": 250000,
            "beneficiary_category_verified": None,
        },
        organization="NSFDC",
    )
    ranked = generate_recommendations(evaluated, relevance=relevance)
    if ranked.top_recommendation:
        assert ranked.top_recommendation.scheme_id != FREE_COACHING_ID
        assert "coach" not in ranked.top_recommendation.scheme_name.lower()
    assert all(a.scheme_id != FREE_COACHING_ID for a in ranked.alternatives)
