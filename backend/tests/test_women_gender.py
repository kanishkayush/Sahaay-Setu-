"""Gender is a first-class profile/query signal. UNKNOWN never becomes MATCH."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.api.chat import process_chat_request
from app.api.router import _map_to_user_profile
from app.eligibility_engine import evaluate_all_schemes, load_scheme
from app.gender import (
    FIT_MATCH,
    FIT_MISMATCH,
    FIT_UNKNOWN,
    extract_gender,
    gender_fit_role,
    is_gender_discovery_query,
    normalize_gender,
    scheme_eligible_gender,
)
from app.main import app
from app.profile_normalization import relevance_from_project_type
from app.rag.language_detect import detect_language_and_intent
from app.rag.memory import clear_session, get_session_profile
from app.rag.query_context import build_retrieval_query
from app.rag.scheme_advisor import build_brief, ui_cards
from app.rag.scheme_knowledge import iter_schemes
from app.recommendation_engine import RelevanceQuery, generate_recommendations, scheme_relevance_priority
from app.schemas.chat import ChatProfile, ChatRequest

client = TestClient(app)
TERM_LOAN = "nsfdc-term-loan"
WOMEN_QUERIES_EN = [
    "scheme for women",
    "I need a scheme for women",
    "what schemes are available for women",
    "show me schemes for women",
    "I am a woman, what schemes can I apply for?",
]
WOMEN_QUERIES_HI = [
    "महिलाओं के लिए योजना",
    "महिलाओं के लिए कौन सी योजनाएं हैं",
    "मैं एक महिला हूँ, मेरे लिए कौन सी योजना है",
]
WOMEN_QUERIES_ROMAN = [
    "mahilaon ke liye yojana",
    "main ek mahila hoon mere liye kaunsi yojana hai",
    "women ke liye scheme chahiye",
]


class _FakeLLM:
    def __init__(self, text='{"intent": "LOAN", "activity": "dairy farming"}'):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


def _women_catalogue():
    return [
        raw
        for raw in iter_schemes()
        if gender_fit_role(raw, "FEMALE") == FIT_MATCH
    ]


def _chat(query: str, session: str, language: str = "en", profile: ChatProfile | None = None, user_id: str | None = None):
    return process_chat_request(
        ChatRequest(
            query=query,
            language=language,
            conversation_id=session,
            guideMe=True,
            profile=profile,
            user_id=user_id,
        )
    )


def _run(query: str, session: str, language: str = "en", profile: ChatProfile | None = None):
    clear_session(session)
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        resp = _chat(query, session, language, profile)
    return resp, get_session_profile(session)


def test_women_only_query():
    for q in WOMEN_QUERIES_EN:
        det = detect_language_and_intent(q)
        assert det.gender == "FEMALE", q
        assert det.intent == "WOMEN_DISCOVERY", q
        assert det.domain is None, q
        assert det.purpose == "UNKNOWN", q
        resp, profile = _run(q, f"women-en-{hash(q)}")
        ids = {c.schemeId for c in (resp.ui_cards or []) if c.schemeId}
        assert TERM_LOAN not in ids, q
        assert "crop" not in (resp.answer or "").lower()
        assert "agriculture" not in (resp.answer or "").lower()
        assert profile.gender == "FEMALE"
        assert profile.projectType not in {"AGRICULTURE", "BUSINESS", "EDUCATION"}
        for card in resp.ui_cards or []:
            if card.schemeId:
                assert card.genderFit == "MATCH"
                assert card.action == "VIEW_DETAILS"


def test_women_only_query_hindi():
    for q in WOMEN_QUERIES_HI:
        det = detect_language_and_intent(q)
        assert det.gender == "FEMALE", q
        assert det.intent == "WOMEN_DISCOVERY", q
        resp, _ = _run(q, f"women-hi-{hash(q)}", language="hi")
        ids = {c.schemeId for c in (resp.ui_cards or []) if c.schemeId}
        assert TERM_LOAN not in ids, q
        assert "फसल" not in (resp.answer or "")
        assert "सावधि ऋण" not in (resp.answer or "")


def test_women_only_query_roman_hindi():
    for q in WOMEN_QUERIES_ROMAN:
        det = detect_language_and_intent(q)
        assert det.gender == "FEMALE", q
        assert normalize_gender(det.gender) == "FEMALE"
        resp, profile = _run(q, f"women-ro-{hash(q)}")
        assert profile.gender == "FEMALE"
        ids = {c.schemeId for c in (resp.ui_cards or []) if c.schemeId}
        assert TERM_LOAN not in ids, q


def test_gender_reaches_recommendation_api():
    from app.api.router import ApplicantProfile, RecommendationRequest

    req = RecommendationRequest(
        language="en",
        profile=ApplicantProfile(
            projectType="OTHER",
            estimatedProjectCost=50000,
            annualFamilyIncome=250000,
            educationStatus="VOCATIONAL",
            gender="FEMALE",
        ),
    )
    mapped = _map_to_user_profile(req)
    assert mapped["gender"] == "FEMALE"
    res = client.post(
        "/v1/recommendations",
        json={
            "language": "en",
            "profile": {
                "projectType": "OTHER",
                "estimatedProjectCost": 50000,
                "annualFamilyIncome": 250000,
                "educationStatus": "VOCATIONAL",
                "gender": "FEMALE",
            },
        },
    )
    assert res.status_code == 200
    body = res.json()
    rec_ids = [
        (r.get("scheme") or {}).get("id") or (r.get("scheme") or {}).get("schemeId")
        for r in body.get("recommendations") or []
    ]
    assert TERM_LOAN not in rec_ids


def test_gender_fit_match():
    msy = load_scheme("nsfdc-msy")
    assert scheme_eligible_gender(msy) == "FEMALE"
    assert gender_fit_role(msy, "FEMALE") == FIT_MATCH
    assert gender_fit_role(msy, "WOMAN") == FIT_MATCH
    assert extract_gender("I am a woman") == "FEMALE"


def test_gender_unknown_not_match():
    term = load_scheme(TERM_LOAN)
    assert scheme_eligible_gender(term) == "ANY"
    assert gender_fit_role(term, "FEMALE") == FIT_UNKNOWN
    assert scheme_relevance_priority(
        term,
        RelevanceQuery(assistance_type="OTHER", domain=None, gender="FEMALE"),
    ) == 0


def test_generic_term_loan_not_women_primary():
    brief = build_brief(domain=None, amount=None, activity=None, lang="en", gender="FEMALE")
    ids = []
    if brief.primary:
        ids.append(brief.primary.facts.scheme_id)
    ids.extend(f.facts.scheme_id for f in brief.alternatives)
    assert TERM_LOAN not in ids
    cards = ui_cards(brief, "en")
    assert all(c.schemeId != TERM_LOAN for c in cards)
    blob = (brief.answer or "").lower()
    assert "term loan" not in blob or "not" in blob
    assert "crop" not in blob

    ranked = generate_recommendations(
        evaluate_all_schemes(
            {
                "purpose": None,
                "project_cost_inr": 50000,
                "family_income_inr": 250000,
                "gender": "FEMALE",
                "beneficiary_category_verified": True,
            },
            organization="NSFDC",
        ),
        relevance=RelevanceQuery(assistance_type="LOAN", domain=None, gender="FEMALE", amount_inr=50000),
    )
    if ranked.top_recommendation:
        assert ranked.top_recommendation.scheme_id != TERM_LOAN
        assert gender_fit_role(load_scheme(ranked.top_recommendation.scheme_id), "FEMALE") == FIT_MATCH
    assert all(a.scheme_id != TERM_LOAN for a in ranked.alternatives)


def test_woman_business():
    det = detect_language_and_intent("I am a woman and I need a business loan")
    assert det.gender == "FEMALE"
    assert det.intent == "BUSINESS"
    assert det.domain == "BUSINESS"
    resp, profile = _run("I am a woman and I need a business loan", "woman-biz")
    assert profile.gender == "FEMALE"
    assert profile.projectType == "BUSINESS"
    ids = {c.schemeId for c in (resp.ui_cards or []) if c.schemeId}
    assert "nsfdc-education" not in ids


def test_woman_education():
    det = detect_language_and_intent("I am a woman and need an education loan")
    assert det.gender == "FEMALE"
    assert det.intent == "EDUCATION_LOAN"
    assert det.domain == "EDUCATION"
    resp, profile = _run("I am a woman and need an education loan", "woman-edu")
    assert profile.projectType == "EDUCATION"
    assert profile.gender == "FEMALE"
    ids = {c.schemeId for c in (resp.ui_cards or []) if c.schemeId}
    assert TERM_LOAN not in ids
    assert "nsfdc-education" in ids or any(
        (c.domain or "").upper() == "EDUCATION" for c in (resp.ui_cards or [])
    )


def test_woman_agriculture():
    det = detect_language_and_intent("I am a woman and need a farming loan")
    assert det.gender == "FEMALE"
    assert det.intent == "AGRICULTURE"
    resp, profile = _run("I am a woman and need a farming loan", "woman-agri")
    assert profile.projectType == "AGRICULTURE"
    assert profile.gender == "FEMALE"
    cards = resp.ui_cards or []
    primary = [c for c in cards if c.isPrimary and c.fitStatus != "RELATED"]
    assert all(c.schemeId != TERM_LOAN for c in primary)


def test_profile_gender():
    prior = ChatProfile(gender="FEMALE")
    rq = build_retrieval_query("I need a scheme", profile=prior)
    assert rq.gender == "FEMALE"
    resp, profile = _run("I need a scheme for women", "profile-gender", profile=ChatProfile(gender="FEMALE"))
    assert profile.gender == "FEMALE"


def test_conversation_gender_does_not_auto_save():
    from app.services.storage import get_profile_store

    user_id = "gender-no-autosave-user"
    store = get_profile_store()
    store.upsert(user_id, {"user_id": user_id, "eligibility": {}})
    clear_session("gender-no-save")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        _chat("I am a woman", "gender-no-save", user_id=user_id)
    saved = store.get(user_id) or {}
    eligibility = saved.get("eligibility") or {}
    assert eligibility.get("gender") in (None, "")
    assert get_session_profile("gender-no-save").gender == "FEMALE"


def test_explicit_gender_save():
    from app.services.storage import get_profile_store

    user_id = "gender-explicit-save-user"
    store = get_profile_store()
    store.upsert(user_id, {"user_id": user_id, "eligibility": {}})
    clear_session("gender-save")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        _chat("remember that I am a woman", "gender-save", user_id=user_id)
    saved = store.get(user_id) or {}
    eligibility = saved.get("eligibility") or {}
    assert eligibility.get("gender") == "FEMALE"


def test_check_eligibility_other_amount_woman():
    relevance = relevance_from_project_type("OTHER", amount_inr=50000, gender="FEMALE")
    assert relevance.gender == "FEMALE"
    assert relevance.domain is None
    res = client.post(
        "/v1/recommendations",
        json={
            "language": "en",
            "profile": {
                "projectType": "OTHER",
                "estimatedProjectCost": 50000,
                "annualFamilyIncome": 250000,
                "educationStatus": "VOCATIONAL",
                "gender": "FEMALE",
            },
        },
    )
    assert res.status_code == 200
    recs = res.json().get("recommendations") or []
    related = res.json().get("relatedOptions") or []
    rec_ids = [(r.get("scheme") or {}).get("id") for r in recs]
    rel_ids = [(r.get("scheme") or {}).get("id") for r in related]
    assert TERM_LOAN not in rec_ids
    for rec in recs:
        scheme = rec.get("scheme") or {}
        sid = scheme.get("id")
        if sid:
            assert gender_fit_role(load_scheme(sid), "FEMALE") == FIT_MATCH


def test_follow_up_gender_keeps_unknown_purpose():
    clear_session("follow-unknown")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        _chat("I need a scheme", "follow-unknown")
        _chat("I am a woman", "follow-unknown")
    profile = get_session_profile("follow-unknown")
    assert profile.gender == "FEMALE"
    assert profile.projectType not in {"AGRICULTURE", "BUSINESS", "EDUCATION"}


def test_follow_up_gender_keeps_business_purpose():
    clear_session("follow-biz")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        _chat("I need a business loan", "follow-biz")
        _chat("I am a woman", "follow-biz")
    profile = get_session_profile("follow-biz")
    assert profile.projectType == "BUSINESS"
    assert profile.gender == "FEMALE"


def test_follow_up_gender_keeps_education_purpose():
    clear_session("follow-edu")
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM()),
        patch("app.rag.retriever.retrieve", return_value=[]),
        patch("app.rag.retriever.retrieve_scheme_context", return_value=[]),
    ):
        _chat("I need an education loan", "follow-edu")
        _chat("I am a woman", "follow-edu")
    profile = get_session_profile("follow-edu")
    assert profile.projectType == "EDUCATION"
    assert profile.gender == "FEMALE"


def test_women_catalogue_metadata_not_hardcoded():
    matches = _women_catalogue()
    assert matches
    assert all(scheme_eligible_gender(raw) == "FEMALE" for raw in matches)
    assert TERM_LOAN not in {raw.get("scheme_id") for raw in matches}


def test_gender_mismatch_male_on_women_scheme():
    msy = load_scheme("nsfdc-msy")
    assert gender_fit_role(msy, "MALE") == FIT_MISMATCH
    assert is_gender_discovery_query("scheme for women")
    assert not is_gender_discovery_query("I am a woman and I need a business loan", "BUSINESS")
