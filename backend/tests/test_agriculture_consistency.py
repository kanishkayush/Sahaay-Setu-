"""RAG/Voice and Check Eligibility must agree on agriculture relevance."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.eligibility_engine import load_scheme
from app.main import app
from app.rag.language_detect import detect_language_and_intent, extract_specific_activity
from app.rag.memory import clear_session, get_session_profile
from app.rag.scheme_advisor import build_brief
from app.recommendation_engine import (
    RelevanceQuery,
    agriculture_activity_family,
    agriculture_fit_role,
    generate_recommendations,
    recommend_from_profile,
)
from app.eligibility_engine import evaluate_all_schemes
from app.schemas.chat import ChatRequest
from app.api.chat import process_chat_request

TERM_ID = "nsfdc-term-loan"
EDU_ID = "nsfdc-education"
FREE_COACHING_ID = "0070a49e-2e01-554a-8f33-e6ee5648877e"
client = TestClient(app)


class _FakeLLM:
    def __init__(self, text="advisory reply"):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


def _check_eligibility(project_type: str, narrative: str | None = None, cost: int = 200000):
    payload = {
        "language": "en",
        "profile": {
            "projectType": project_type,
            "estimatedProjectCost": cost,
            "annualFamilyIncome": 300000,
            "educationStatus": "VOCATIONAL" if project_type != "EDUCATION" else "GRADUATE",
            "gender": "MALE",
        },
    }
    if narrative:
        payload["profile"]["narrative"] = narrative
    return client.post("/v1/recommendations", json=payload)


def _primary_ids(body: dict) -> list[str]:
    recs = body.get("recommendations") or []
    ids = []
    for rec in recs:
        scheme = rec.get("scheme") or {}
        sid = scheme.get("id") or scheme.get("schemeId")
        if rec.get("fitStatus") == "RELATED":
            continue
        if sid:
            ids.append(sid)
    return ids


def _related_ids(body: dict) -> list[str]:
    items = body.get("relatedOptions") or []
    ids = []
    for rec in items:
        assert rec.get("fitStatus") == "RELATED"
        scheme = rec.get("scheme") or {}
        sid = scheme.get("id") or scheme.get("schemeId")
        if sid:
            ids.append(sid)
    return ids


def _chat(query: str, session: str, language: str = "en"):
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("advisory reply")):
        return process_chat_request(
            ChatRequest(query=query, language=language, conversation_id=session, guideMe=True)
        )


def test_term_loan_agriculture_role_is_related_not_match():
    scheme = load_scheme(TERM_ID)
    for activity in (
        "RICE_FARMING",
        "CROP_FARMING",
        "DAIRY_FARMING",
        "LIVESTOCK",
        "POULTRY",
        "FARMING",
    ):
        assert agriculture_fit_role(scheme, activity, "AGRICULTURE") == "related"
    assert agriculture_fit_role(scheme, None, "BUSINESS") != "match"


def test_gbs_is_not_a_crop_match():
    scheme = load_scheme("nsfdc-gbs")
    assert agriculture_fit_role(scheme, "RICE_FARMING", "AGRICULTURE") == "none"


def test_related_cannot_become_primary():
    evaluated = evaluate_all_schemes(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    ranked = generate_recommendations(
        evaluated,
        relevance=RelevanceQuery(
            assistance_type="LOAN",
            domain="AGRICULTURE",
            activity="RICE_FARMING",
            amount_inr=200000,
        ),
    )
    assert ranked.top_recommendation is None or ranked.top_recommendation.scheme_id != TERM_ID
    related_ids = {s.scheme_id for s in ranked.related}
    alt_ids = {s.scheme_id for s in ranked.alternatives}
    assert TERM_ID not in alt_ids
    if ranked.top_recommendation:
        assert ranked.top_recommendation.scheme_id not in related_ids
    if TERM_ID in related_ids:
        assert ranked.top_recommendation is None or ranked.top_recommendation.scheme_id != TERM_ID


def test_activity_families_language_independent():
    cases = [
        ("I need a loan for crop farming", "CROP_FARMING"),
        ("मुझे फसल की खेती के लिए लोन चाहिए", "CROP_FARMING"),
        ("mujhe fasal ki kheti ke liye loan chahiye", "CROP_FARMING"),
        ("I need a loan for rice farming", "RICE_FARMING"),
        ("I need a dairy farming loan", "DAIRY_FARMING"),
        ("मुझे डेयरी के लिए लोन चाहिए", "DAIRY_FARMING"),
        ("mujhe dairy ke liye loan chahiye", "DAIRY_FARMING"),
        ("I need a livestock loan", "LIVESTOCK"),
    ]
    for query, activity in cases:
        det = detect_language_and_intent(query)
        assert det.domain == "AGRICULTURE"
        assert extract_specific_activity(query) == activity
        family = agriculture_activity_family(det.activity or activity, det.domain)
        if activity == "RICE_FARMING":
            assert family == "CROP_FARMING"
        elif activity == "CROP_FARMING":
            assert family == "CROP_FARMING"
        elif activity == "DAIRY_FARMING":
            assert family == "DAIRY_FARMING"
        else:
            assert family == "LIVESTOCK"


def test_rag_and_check_eligibility_agree_on_agriculture_queries():
    queries = [
        ("I need a loan for rice farming", "en", "AGRICULTURE"),
        ("मुझे फसल की खेती के लिए लोन चाहिए", "hi", "AGRICULTURE"),
        ("mujhe fasal ki kheti ke liye loan chahiye", "hi", "AGRICULTURE"),
        ("I need a dairy farming loan", "en", "AGRICULTURE"),
        ("मुझे डेयरी के लिए लोन चाहिए", "hi", "AGRICULTURE"),
        ("I need a livestock loan", "en", "ANIMAL_HUSBANDRY"),
    ]
    for query, lang, project_type in queries:
        resp = _chat(query, f"sess-agri-{query[:12]}", lang)
        profile = get_session_profile(f"sess-agri-{query[:12]}")
        assert profile.recommendedSchemeId != TERM_ID
        cards = [c for c in (resp.ui_cards or []) if getattr(c, "type", None) and c.type.value == "SCHEME_CARD"]
        for card in cards:
            if card.schemeId == TERM_ID:
                assert card.fitStatus == "RELATED"
                assert card.isPrimary is not True
                assert card.action == "VIEW_DETAILS"

        brief = build_brief(
            domain="AGRICULTURE",
            amount=200000,
            activity=extract_specific_activity(query),
            lang="hi" if lang == "hi" else "en",
            query=query,
        )
        assert brief.primary is None

        elig = _check_eligibility(project_type, narrative=query)
        assert elig.status_code == 200
        body = elig.json()
        assert TERM_ID not in _primary_ids(body)
        assert FREE_COACHING_ID not in _primary_ids(body)
        related = _related_ids(body)
        if TERM_ID in related:
            assert TERM_ID not in _primary_ids(body)


def test_business_term_loan_still_recommended():
    elig = _check_eligibility("RETAIL_SHOP", narrative="I need a business loan", cost=200000)
    assert elig.status_code == 200
    ids = _primary_ids(elig.json())
    assert ids
    assert TERM_ID in ids or ids[0] in {"nsfdc-uny", "nsfdc-mfs", "nsfdc-amy", TERM_ID}
    ranked = recommend_from_profile(
        {
            "purpose": "small_retail",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        relevance=RelevanceQuery(assistance_type="LOAN", domain="BUSINESS", amount_inr=200000),
    )
    assert ranked.top_recommendation is not None
    assert ranked.top_recommendation.scheme_id == TERM_ID


def test_education_catalogue_intact():
    elig = _check_eligibility("EDUCATION", narrative="I want an education loan", cost=400000)
    assert elig.status_code == 200
    ids = _primary_ids(elig.json())
    assert EDU_ID in ids
    resp = _chat("I want an education loan", "sess-edu-en", "en")
    profile = get_session_profile("sess-edu-en")
    assert profile.recommendedSchemeId == EDU_ID
    hi = _chat("मुझे पढ़ाई के लिए लोन चाहिए", "sess-edu-hi", "hi")
    assert get_session_profile("sess-edu-hi").recommendedSchemeId == EDU_ID
    roman = _chat("mujhe padhai ke liye loan chahiye", "sess-edu-roman", "hi")
    assert get_session_profile("sess-edu-roman").recommendedSchemeId == EDU_ID
    assert EDU_ID in (resp.related_scheme_ids or [])
    assert EDU_ID in (hi.related_scheme_ids or [])
    assert EDU_ID in (roman.related_scheme_ids or [])


def test_business_context_does_not_contaminate_rice_farming():
    session = "sess-biz-then-rice"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("advisory reply")):
        process_chat_request(
            ChatRequest(query="I need a business loan", language="en", conversation_id=session, guideMe=True)
        )
        process_chat_request(
            ChatRequest(query="2 lakh", language="en", conversation_id=session, guideMe=True)
        )
        process_chat_request(
            ChatRequest(query="mobile repair shop", language="en", conversation_id=session, guideMe=True)
        )
        rice = process_chat_request(
            ChatRequest(query="I need a loan for rice farming", language="en", conversation_id=session, guideMe=True)
        )
    profile = get_session_profile(session)
    assert profile.projectType == "AGRICULTURE"
    assert profile.recommendedSchemeId != TERM_ID
    cards = [c for c in (rice.ui_cards or []) if getattr(c, "type", None) and c.type.value == "SCHEME_CARD"]
    for card in cards:
        if card.schemeId == TERM_ID:
            assert card.fitStatus == "RELATED"
            assert card.isPrimary is not True
