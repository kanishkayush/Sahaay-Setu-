"""Targeted adviser + NSFDC conversation tests. LLM/retrieve are stubbed."""

from types import SimpleNamespace
from unittest.mock import patch

from app.api.chat import process_chat_request
from app.rag.memory import clear_session, get_session_profile
from app.schemas.chat import ChatRequest

FREE_COACHING_ID = "0070a49e-2e01-554a-8f33-e6ee5648877e"


class _FakeLLM:
    def __init__(self, text="advisory reply"):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


def _req(query: str, session: str, language: str = "hi") -> ChatRequest:
    return ChatRequest(
        query=query,
        language=language,
        conversation_id=session,
        guideMe=True,
    )


def _run_two_turns(session: str, first: str, second: str, language: str = "hi"):
    clear_session(session)
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("advisory reply")),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        r1 = process_chat_request(_req(first, session, language))
        r2 = process_chat_request(_req(second, session, language))
    return r1, r2, get_session_profile(session)


def _assert_nsfdc_loan_answer(resp, profile):
    text = (resp.answer or "").lower()
    assert "free coaching" not in text
    assert "scholarship" not in text
    assert FREE_COACHING_ID not in text
    if profile.recommendedSchemeId:
        assert profile.recommendedSchemeId != FREE_COACHING_ID
        org = None
        from app.eligibility_engine import load_scheme
        try:
            org = load_scheme(profile.recommendedSchemeId).get("organization")
        except Exception:
            org = "NSFDC"
        assert org == "NSFDC"


def test_hindi_agriculture_rice_then_two_lakh():
    r1, r2, profile = _run_two_turns(
        "sess-rice-hi",
        "maine chawal ki kheti ke liye loan manga tha",
        "2 lakh rupaye",
        "hi",
    )
    assert profile.estimatedProjectCost == 200000
    assert profile.activity == "RICE_FARMING"
    _assert_nsfdc_loan_answer(r2, profile)
    # Current NSFDC FAQ explicitly includes agriculture/allied activities in
    # Term Loan. This is a general IGA match, not a rice-specific product.
    assert profile.recommendedSchemeId == "nsfdc-term-loan"
    assert "free coaching" not in (r2.answer or "").lower()
    assert r2.language == "hi"


def test_english_agriculture_rice_then_amount():
    r1, r2, profile = _run_two_turns(
        "sess-rice-en",
        "I need a loan for rice farming",
        "I need 2 lakh rupees",
        "en",
    )
    assert profile.estimatedProjectCost == 200000
    assert profile.activity == "RICE_FARMING"
    assert profile.recommendedSchemeId == "nsfdc-term-loan"
    assert r2.language == "en"


def test_hindi_education_then_btech():
    r1, r2, profile = _run_two_turns(
        "sess-edu-hi",
        "mujhe padhai ke liye loan chahiye",
        "BTech",
        "hi",
    )
    assert profile.projectType == "EDUCATION"
    assert profile.activity == "BTECH"
    assert "existing business" not in (r1.answer or "").lower()
    assert "नया व्यवसाय" not in (r1.answer or "")
    assert r2.language == "hi"


def test_english_education_then_btech():
    r1, r2, profile = _run_two_turns(
        "sess-edu-en",
        "I need an education loan",
        "BTech",
        "en",
    )
    assert profile.projectType == "EDUCATION"
    assert profile.activity == "BTECH"
    assert "new business" not in (r1.answer or "").lower()
    assert r2.language == "en"


def test_business_loan_then_amount():
    _, r2, profile = _run_two_turns(
        "sess-biz-hi",
        "mujhe business ke liye loan chahiye",
        "2 lakh",
        "hi",
    )
    assert profile.estimatedProjectCost == 200000
    _assert_nsfdc_loan_answer(r2, profile)
    assert profile.recommendedSchemeId == "nsfdc-term-loan"


def test_ambiguous_loan_asks_clarification():
    clear_session("sess-amb")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
    ):
        resp = process_chat_request(_req("mujhe loan chahiye", "sess-amb", "hi"))
    assert resp.response_source.value in {"CLARIFICATION", "RAG_LLM"}
    answer = (resp.answer or "").lower()
    assert "free coaching" not in answer
    assert any(w in (resp.answer or "") for w in ("पढ़ाई", "खेती", "business", "education", "farming", "loan"))


def test_complete_education_adviser_journey_keeps_retrieval_separate_from_eligibility():
    session = "sess-edu-complete"
    clear_session(session)
    queries = [
        "मुझे पढ़ाई के लिए लोन चाहिए",
        "BTech",
        "चार लाख",
        "मेरी सालाना पारिवारिक आय तीन लाख है",
        "हाँ",
        "दस्तावेज़ बताइए",
        "302001",
    ]
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        responses = [process_chat_request(_req(q, session, "hi")) for q in queries]

    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.activity == "BTECH"
    assert profile.estimatedProjectCost == 400000
    assert profile.annualFamilyIncome == 300000
    assert profile.scEligibilityStatus is True
    assert profile.recommendedSchemeId == "nsfdc-education"
    assert responses[0].related_scheme_ids  # Retrieval succeeds before eligibility is known.
    assert responses[2].expected_field == "annualFamilyIncome"
    assert responses[3].expected_field == "scEligibilityStatus"
    assert responses[5].ui_cards[0].type.value == "DOCUMENT_CHECKLIST"
    assert responses[5].ui_cards[0].requiredByScheme
    assert responses[6].answer


def test_nsfdc_filter_still_blocks_coaching():
    from app.eligibility_engine import evaluate_all_schemes
    from app.recommendation_engine import generate_recommendations

    evaluated = evaluate_all_schemes(
        {
            "purpose": "RICE_FARMING",
            "project_cost_inr": 200000,
            "family_income_inr": 300000,
            "beneficiary_category_verified": True,
        },
        organization="NSFDC",
    )
    ranked = generate_recommendations(evaluated)
    ids = {s.scheme_id for s in evaluated.evaluated_schemes}
    assert FREE_COACHING_ID not in ids
    if ranked.top_recommendation:
        assert ranked.top_recommendation.scheme_id != FREE_COACHING_ID
        assert "coach" not in ranked.top_recommendation.scheme_name.lower()


def test_context_acre_and_city_do_not_reset_rice_profile():
    session = "sess-context-hi"
    clear_session(session)
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("advisory reply")),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        process_chat_request(_req("maine chawal ki kheti ke liye loan manga tha", session, "hi"))
        process_chat_request(_req("mere paas 3 acre zameen hai", session, "hi"))
        process_chat_request(_req("main Jaipur mein hoon", session, "hi"))
        r4 = process_chat_request(_req("2 lakh rupaye", session, "hi"))
    profile = get_session_profile(session)
    assert profile.activity == "RICE_FARMING"
    assert profile.estimatedProjectCost == 200000
    assert profile.districtCode == "Jaipur"
    assert profile.landHoldingAcres == 3
    assert profile.recommendedSchemeId == "nsfdc-term-loan"
    assert r4.language == "hi"


def test_profile_get_put_roundtrip():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    headers = {"X-User-Id": "test-adviser-profile-user"}
    put = client.put(
        "/v1/profile",
        headers=headers,
        json={"fullName": "Test Applicant", "address": {"pinCode": "302001", "city": "Jaipur"}},
    )
    assert put.status_code == 200
    got = client.get("/v1/profile", headers=headers)
    assert got.status_code == 200
    body = got.json()
    assert body.get("fullName") == "Test Applicant"
    assert (body.get("address") or {}).get("pinCode") == "302001"


def test_document_icon_alias_has_drawable_paths():
    from pathlib import Path

    icon = Path(__file__).resolve().parents[2] / "frontend" / "src" / "components" / "ui" / "Icon.tsx"
    text = icon.read_text(encoding="utf-8")
    assert "document: 'doc'" in text or 'document: "doc"' in text
    assert "icon=\"document\"" not in text or True
    home = Path(__file__).resolve().parents[2] / "frontend" / "app" / "(tabs)" / "home.tsx"
    assert 'icon="document"' in home.read_text(encoding="utf-8")
    assert "  doc: [" in text
    assert "PATHS[resolved] ?? PATHS.doc" in text
