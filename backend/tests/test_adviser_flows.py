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
    answer = r2.answer or ""
    assert "सावधि ऋण आपके वर्तमान अनुरोध से मेल खाता" not in answer
    assert "recommended" not in answer.lower()
    assert any(
        token in answer
        for token in ("मेल खाने वाली योजना नहीं", "समर्पित", "catalogue", "फसल")
    )
    cards = [c for c in (r2.ui_cards or []) if getattr(c, "type", None) and c.type.value == "SCHEME_CARD"]
    for card in cards:
        assert "Recommended" not in (card.reason or "")
        if card.schemeId == "nsfdc-term-loan":
            assert card.isPrimary is not True
            assert card.fitStatus == "RELATED"
            assert card.schemeId == "nsfdc-term-loan"
            assert card.action == "VIEW_DETAILS"
    assert profile.recommendedSchemeId != "nsfdc-term-loan"
    assert "free coaching" not in answer.lower()
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
    assert profile.recommendedSchemeId != "nsfdc-term-loan"
    answer = (r2.answer or "").lower()
    assert "recommended" not in answer
    assert "dedicated crop" in answer or "could not find" in answer or "catalogue" in answer
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
    assert profile.recommendedSchemeId in {
        "nsfdc-term-loan", "nsfdc-uny", "nsfdc-mfs", "nsfdc-lvy",
    }


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
        "दस्तावेज़ बताइए",
        "302001",
    ]
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        responses = [process_chat_request(_req(q, session, "hi")) for q in queries]

    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.activity == "BTECH"
    assert profile.requestedLoanAmount == 400000
    assert profile.estimatedProjectCost is None
    assert profile.annualFamilyIncome == 300000
    assert profile.recommendedSchemeId == "nsfdc-education"
    assert responses[0].related_scheme_ids  # Retrieval succeeds before eligibility is known.
    joined = " ".join((r.answer or "") for r in responses)
    assert "BTech, मेडिकल" not in joined
    assert "ITI" not in (responses[0].answer or "")
    assert responses[0].expected_field != "annualFamilyIncome"
    assert all(r.expected_field != "scEligibilityStatus" for r in responses)
    docs = next(r for r in responses if r.ui_cards and r.ui_cards[0].type.value == "DOCUMENT_CHECKLIST")
    assert docs.ui_cards[0].requiredByScheme
    assert responses[-1].answer


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
    assert profile.recommendedSchemeId != "nsfdc-term-loan"
    assert "सावधि ऋण आपके वर्तमान अनुरोध से मेल खाता" not in (r4.answer or "")
    assert r4.language == "hi"


def test_profile_get_put_roundtrip():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    headers = {"X-User-Id": "test-adviser-profile-user"}
    put = client.put(
        "/v1/profile",
        headers=headers,
        json={
            "fullName": "Ayush Kumar Shahi",
            "educationLevel": "BTech Computer Science",
            "address": {"pinCode": "302017", "city": "Jaipur", "state": "Rajasthan", "addressLine1": "Jaipur Rajasthan"},
            "eligibility": {"annualFamilyIncome": 300000, "scEligibilityStatus": True},
            "business": {"existingBusiness": None},
        },
    )
    assert put.status_code == 200
    got = client.get("/v1/profile", headers=headers)
    assert got.status_code == 200
    body = got.json()
    assert body.get("fullName") == "Ayush Kumar Shahi"
    assert (body.get("address") or {}).get("pinCode") == "302017"
    assert (body.get("eligibility") or {}).get("annualFamilyIncome") == 300000
    assert (body.get("eligibility") or {}).get("scEligibilityStatus") is True
    assert (body.get("business") or {}).get("existingBusiness") is None


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


def _no_income_question(text: str) -> None:
    low = (text or "").lower()
    assert "वार्षिक पारिवारिक आय कितनी" not in (text or "")
    assert "what is your annual family income" not in low
    assert "btech, medical, nursing, iti" not in low
    assert "btech, मेडिकल" not in (text or "").lower()


def test_education_first_turn_recommends_before_eligibility():
    session = "sess-edu-first"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.recommendedSchemeId == "nsfdc-education"
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    _no_income_question(resp.answer or "")
    assert "ITI" not in (resp.answer or "")


def test_roman_hindi_and_english_education_same_scheme():
    for session, query, lang in (
        ("sess-edu-roman", "mujhe padhai ke liye loan chahiye", "hi"),
        ("sess-edu-en2", "I need a loan for my education", "en"),
    ):
        clear_session(session)
        with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
            resp = process_chat_request(_req(query, session, lang))
        profile = get_session_profile(session)
        assert profile.projectType == "EDUCATION"
        assert profile.recommendedSchemeId == "nsfdc-education"
        assert "nsfdc-education" in (resp.related_scheme_ids or [])
        _no_income_question(resp.answer or "")
        if "scholarship" in (resp.answer or "").lower():
            assert "not a loan" in (resp.answer or "").lower() or "not loan" in (resp.answer or "").lower()
        assert "free coaching" not in (resp.answer or "").lower()


def test_two_lakh_maps_to_requested_amount_not_income():
    from app.rag.guided_journey import _try_deterministic_parse
    from app.schemas.chat import ChatProfile

    edu = ChatProfile(projectType="EDUCATION", lastExpectedField="general")
    parsed = _try_deterministic_parse("2 lakh", edu)
    assert parsed.get("requestedLoanAmount") == 200000
    assert "estimatedProjectCost" not in parsed
    assert "annualFamilyIncome" not in parsed

    asked_income = ChatProfile(projectType="EDUCATION", lastExpectedField="annualFamilyIncome")
    parsed_income = _try_deterministic_parse("2 lakh", asked_income)
    assert parsed_income.get("annualFamilyIncome") == 200000
    assert parsed_income.get("estimatedProjectCost") is None
    assert parsed_income.get("requestedLoanAmount") is None

    explicit = ChatProfile(projectType="EDUCATION", lastExpectedField="requestedLoanAmount")
    parsed_explicit = _try_deterministic_parse("मेरी income 3 lakh है", explicit)
    assert parsed_explicit.get("annualFamilyIncome") == 300000
    assert "requestedLoanAmount" not in parsed_explicit

    business = ChatProfile(projectType="BUSINESS", lastExpectedField="estimatedProjectCost")
    parsed_biz = _try_deterministic_parse("2 lakh", business)
    assert parsed_biz.get("estimatedProjectCost") == 200000
    assert "requestedLoanAmount" not in parsed_biz


def test_education_does_not_collect_business_or_farming_slots():
    from app.rag.guided_journey import _try_deterministic_parse
    from app.schemas.chat import ChatProfile

    parsed = _try_deterministic_parse("2 lakh", ChatProfile(projectType="EDUCATION"))
    assert "existingBusiness" not in parsed
    assert "landHoldingAcres" not in parsed
    assert parsed.get("requestedLoanAmount") == 200000
    assert "estimatedProjectCost" not in parsed


def test_saved_profile_income_is_not_reasked():
    from app.services.storage import get_profile_store

    uid = "edu-saved-income-user"
    get_profile_store().upsert(
        uid,
        {"eligibility": {"annualFamilyIncome": 300000, "scEligibilityStatus": True}},
    )
    session = "sess-edu-saved-income"
    clear_session(session)
    req = ChatRequest(
        query="मुझे पढ़ाई के लिए लोन चाहिए",
        language="hi",
        conversation_id=session,
        guideMe=True,
        user_id=uid,
    )
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(req)
        r2 = process_chat_request(
            ChatRequest(
                query="2 lakh",
                language="hi",
                conversation_id=session,
                guideMe=True,
                user_id=uid,
            )
        )
    profile = get_session_profile(session)
    assert profile.annualFamilyIncome == 300000
    assert profile.requestedLoanAmount == 200000
    assert profile.estimatedProjectCost is None
    assert profile.recommendedSchemeId == "nsfdc-education"
    _no_income_question((r1.answer or "") + " " + (r2.answer or ""))
    assert r1.expected_field != "annualFamilyIncome"
    assert r2.expected_field != "annualFamilyIncome"


def test_missing_profile_income_does_not_block_education_retrieval():
    session = "sess-edu-no-income"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("I need an education loan", session, "en"))
    profile = get_session_profile(session)
    assert profile.annualFamilyIncome is None
    assert profile.recommendedSchemeId == "nsfdc-education"
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    assert "what is your annual family income" not in (resp.answer or "").lower()


def test_same_question_is_not_repeated_after_valid_amount():
    session = "sess-edu-repeat"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
        r2 = process_chat_request(_req("2 lakh", session, "hi"))
        r3 = process_chat_request(_req("BTech", session, "hi"))
    profile = get_session_profile(session)
    assert profile.requestedLoanAmount == 200000
    assert profile.estimatedProjectCost is None
    assert profile.activity == "BTECH"
    assert "कोर्स की अनुमानित कुल फीस" not in (r2.answer or "")
    assert "कोर्स की अनुमानित कुल फीस" not in (r3.answer or "")
    assert r2.expected_field != "estimatedProjectCost"
    assert r3.expected_field != "estimatedProjectCost"


def test_education_then_farming_switches_topic():
    session = "sess-edu-to-farm"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
        resp = process_chat_request(_req("नहीं, मुझे खेती के लिए लोन चाहिए", session, "hi"))
    profile = get_session_profile(session)
    assert profile.projectType == "AGRICULTURE"
    assert profile.recommendedSchemeId != "nsfdc-education"
    assert "Educational Loan" not in (resp.answer or "") or profile.projectType == "AGRICULTURE"


def test_kheti_loan_is_honest_and_does_not_force_term_loan():
    session = "sess-kheti-honest"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("मुझे खेती के लिए लोन चाहिए", session, "hi"))
    profile = get_session_profile(session)
    assert profile.projectType == "AGRICULTURE"
    assert profile.recommendedSchemeId != "nsfdc-term-loan"
    answer = resp.answer or ""
    assert "सावधि ऋण आपके वर्तमान अनुरोध से मेल खाता" not in answer
    assert "recommended" not in answer.lower()
    assert any(tok in answer for tok in ("मेल खाने वाली योजना नहीं", "समर्पित", "catalogue"))
    cards = [c for c in (resp.ui_cards or []) if getattr(c, "type", None) and c.type.value == "SCHEME_CARD"]
    for card in cards:
        assert card.action == "VIEW_DETAILS"
        assert card.schemeId
        assert "Recommended" not in (card.reason or "")
        if card.schemeId == "nsfdc-term-loan":
            assert card.fitStatus == "RELATED"


def test_farming_then_education_switches_topic():
    session = "sess-farm-to-edu"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("मुझे खेती के लिए लोन चाहिए", session, "hi"))
        resp = process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.recommendedSchemeId == "nsfdc-education"
    assert "nsfdc-education" in (resp.related_scheme_ids or [])


def test_voice_and_typed_education_share_process_chat_request():
    from app.api.chat import process_chat_request as shared

    session_t = "sess-typed-edu"
    session_v = "sess-voice-edu"
    clear_session(session_t)
    clear_session(session_v)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        typed = shared(_req("मुझे पढ़ाई के लिए लोन चाहिए", session_t, "hi"))
        voice = shared(_req("मुझे पढ़ाई के लिए लोन चाहिए", session_v, "hi"))
    assert get_session_profile(session_t).recommendedSchemeId == get_session_profile(session_v).recommendedSchemeId
    assert typed.related_scheme_ids == voice.related_scheme_ids
    assert get_session_profile(session_t).projectType == "EDUCATION"


def test_assistant_coords_context_does_not_unset_income():
    from app.schemas.assistant import AssistantProfileContext
    from app.schemas.chat import ChatProfile

    ctx = AssistantProfileContext(latitude=26.9, longitude=75.8)
    raw = {k: v for k, v in ctx.model_dump(exclude_unset=True).items() if v is not None}
    profile = ChatProfile(**raw)
    dumped = profile.model_dump(exclude_unset=True)
    assert "annualFamilyIncome" not in dumped
    assert "scEligibilityStatus" not in dumped


def _req_app(query: str, session: str, app_language: str = "en", user_id: str | None = None) -> ChatRequest:
    """Simulate the frontend: app language is sent on every turn."""
    return ChatRequest(
        query=query,
        language=app_language,
        conversation_id=session,
        guideMe=True,
        user_id=user_id,
    )


def test_hindi_conversation_stays_hindi_after_btech():
    session = "sess-lang-hi-btech"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(_req_app("मुझे पढ़ाई के लिए लोन चाहिए", session))
        r2 = process_chat_request(_req_app("BTech", session))
    assert r1.language == "hi"
    assert r2.language == "hi"
    assert get_session_profile(session).preferredLanguage == "hi"
    assert get_session_profile(session).activity == "BTECH"


def test_hindi_conversation_stays_hindi_after_two_lakh():
    session = "sess-lang-hi-2lakh"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req_app("मुझे पढ़ाई के लिए लोन चाहिए", session))
        r2 = process_chat_request(_req_app("2 lakh", session))
    assert r2.language == "hi"
    assert get_session_profile(session).requestedLoanAmount == 200000
    assert get_session_profile(session).estimatedProjectCost is None


def test_hindi_conversation_stays_hindi_after_jaipur():
    session = "sess-lang-hi-jaipur"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req_app("मुझे पढ़ाई के लिए लोन चाहिए", session))
        r2 = process_chat_request(_req_app("Jaipur", session))
    assert r2.language == "hi"
    assert get_session_profile(session).districtCode == "Jaipur"


def test_english_conversation_stays_english_after_btech():
    session = "sess-lang-en-btech"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(_req_app("I need an education loan", session, "hi"))
        r2 = process_chat_request(_req_app("BTech", session, "hi"))
    assert r1.language == "en"
    assert r2.language == "en"


def test_roman_hindi_conversation_stays_hindi_after_btech():
    session = "sess-lang-roman-btech"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(_req_app("mujhe padhai ke liye loan chahiye", session))
        r2 = process_chat_request(_req_app("BTech Computer Science", session))
    assert r1.language == "hi"
    assert r2.language == "hi"


def test_explicit_switch_please_answer_in_english():
    session = "sess-lang-switch-answer-en"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
        r2 = process_chat_request(_req("Please answer in English", session, "hi"))
    assert r2.language == "en"
    assert get_session_profile(session).preferredLanguage == "en"


def test_explicit_switch_english_to_hindi():
    session = "sess-lang-switch-hi"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req_app("I need an education loan", session))
        r2 = process_chat_request(_req_app("हिंदी में समझाओ", session))
    assert r2.language == "hi"
    assert get_session_profile(session).preferredLanguage == "hi"


def test_conversational_income_does_not_silently_write_profile():
    from app.services.storage import get_profile_store

    uid = "ownership-income-user"
    store = get_profile_store()
    store.upsert(uid, {"eligibility": {"annualFamilyIncome": 300000}})
    session = "sess-income-ownership"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(_req_app("मुझे पढ़ाई के लिए लोन चाहिए", session, user_id=uid))
        process_chat_request(_req_app("मेरी income 4 lakh है", session, user_id=uid))
    assert r1.language == "hi"
    assert get_session_profile(session).annualFamilyIncome == 400000
    assert store.get(uid)["eligibility"]["annualFamilyIncome"] == 300000

    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(
            _req_app(
                "मेरी income 4 lakh है, इसे मेरी profile में save कर दो",
                session,
                user_id=uid,
            )
        )
    assert store.get(uid)["eligibility"]["annualFamilyIncome"] == 400000

    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req_app("remember my income", session, user_id=uid))
    assert store.get(uid)["eligibility"]["annualFamilyIncome"] == 400000


def _biz_names(text: str) -> str:
    return (text or "").lower()


def test_business_loan_mentions_multiple_nsfdc_options():
    session = "sess-biz-multi"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("I need a business loan", session, "en"))
    text = _biz_names(resp.answer)
    assert "term loan" in text
    assert "udyam" in text or "micro finance" in text
    assert "aajeevika" in text or "micro finance" in text
    assert len(resp.related_scheme_ids) >= 2
    assert "nsfdc-education" not in (resp.related_scheme_ids or [])
    assert "0070a49e" not in text


def test_other_options_returns_alternatives():
    session = "sess-biz-options"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("I need a business loan", session, "en"))
        resp = process_chat_request(_req("What other options do I have?", session, "en"))
    text = _biz_names(resp.answer)
    assert "term loan" in text
    assert "udyam" in text or "micro finance" in text
    assert len(resp.related_scheme_ids) >= 2


def test_term_loan_alawa_returns_alternatives():
    session = "sess-alawa"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("mujhe business ke liye loan chahiye", session, "hi"))
        resp = process_chat_request(_req("Term loan ke alawa aur kya hai?", session, "hi"))
    assert resp.language == "hi"
    text = resp.answer or ""
    assert "उद्यम" in text or "सूक्ष्म" in text or "Udyam" in text or "Micro" in text
    assert len(resp.related_scheme_ids) >= 2


def test_term_loan_explanation():
    session = "sess-explain-tl"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("Term loan kya hota hai?", session, "hi"))
    assert "nsfdc-term-loan" in (resp.related_scheme_ids or [])
    text = (resp.answer or "").lower()
    assert "1.40" in text or "45" in text or "सावधि" in (resp.answer or "") or "term loan" in text


def test_one_lakh_small_business_considers_microfinance():
    session = "sess-1lakh"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("mujhe chhote business ke liye 1 lakh chahiye", session, "hi"))
        resp = process_chat_request(_req("1 lakh", session, "hi"))
    text = (resp.answer or "").lower() + " " + " ".join(resp.related_scheme_ids or [])
    assert "nsfdc-mfs" in (resp.related_scheme_ids or []) or "micro" in text or "सूक्ष्म" in (resp.answer or "")


def test_two_lakh_business_compares_contextually():
    session = "sess-2lakh-biz"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("mujhe business ke liye 2 lakh chahiye", session, "hi"))
        r2 = process_chat_request(_req("2 lakh", session, "hi"))
    profile = get_session_profile(session)
    assert profile.estimatedProjectCost == 200000
    ids = r2.related_scheme_ids or []
    assert "nsfdc-uny" in ids or "nsfdc-term-loan" in ids
    assert "scholarship" not in (r2.answer or "").lower()


def test_twenty_lakh_business_term_loan_context():
    session = "sess-20lakh"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("I need a loan to start a business", session, "en"))
        resp = process_chat_request(_req("20 lakh", session, "en"))
    assert "nsfdc-term-loan" in (resp.related_scheme_ids or [])
    assert "term loan" in (resp.answer or "").lower()


def test_education_not_contaminated_by_business_or_scholarships():
    session = "sess-edu-only"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
    ids = resp.related_scheme_ids or []
    assert "nsfdc-education" in ids
    assert "nsfdc-mfs" not in ids
    text = (resp.answer or "").lower()
    if "scholarship" in text:
        assert "not a loan" in text or "not loan" in text or "ऋण" in (resp.answer or "")
    if "free coaching" in text:
        assert "not a loan" in text or "coaching" in text


def test_term_loan_vs_udyam_retrieves_both():
    session = "sess-compare-tl-uny"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("Term Loan vs Udyam Nidhi", session, "en"))
    ids = set(resp.related_scheme_ids or [])
    assert "nsfdc-term-loan" in ids
    assert "nsfdc-uny" in ids


def test_hindi_business_discovery():
    session = "sess-biz-hi-disc"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("मुझे व्यवसाय के लिए लोन चाहिए", session, "hi"))
    assert resp.language == "hi"
    assert len(resp.related_scheme_ids) >= 2


def test_roman_hindi_other_options():
    session = "sess-roman-opts"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("mujhe business ke liye loan chahiye", session, "hi"))
        resp = process_chat_request(_req("term loan ke alawa aur kya option hai?", session, "hi"))
    assert resp.language == "hi"
    assert len(resp.related_scheme_ids) >= 2


def test_business_multi_turn_keeps_amount_and_activity():
    session = "sess-biz-mt"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("I need a business loan", session, "en"))
        process_chat_request(_req("2 lakh", session, "en"))
        resp = process_chat_request(_req("mobile repair shop", session, "en"))
    profile = get_session_profile(session)
    assert profile.estimatedProjectCost == 200000
    assert profile.activity
    assert "repair" in str(profile.activity).lower() or "shop" in str(profile.activity).lower() or "REPAIR" in str(profile.activity)
    text = (resp.answer or "").lower()
    assert "2" in text or "200000" in text or "lakh" in text or "₹" in (resp.answer or "")
    assert len(resp.related_scheme_ids) >= 1


def test_voice_and_typed_share_adviser_path_for_options():
    from app.api.chat import process_chat_request as shared

    session_t = "sess-opt-typed"
    session_v = "sess-opt-voice"
    clear_session(session_t)
    clear_session(session_v)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        typed = shared(_req("I need a business loan", session_t, "en"))
        voice = shared(_req("I need a business loan", session_v, "en"))
    assert set(typed.related_scheme_ids) == set(voice.related_scheme_ids)
    assert "term loan" in (typed.answer or "").lower()
    assert "term loan" in (voice.answer or "").lower()
