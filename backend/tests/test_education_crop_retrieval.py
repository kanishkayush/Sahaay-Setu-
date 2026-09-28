"""Education and crop-farming retrieval must not collapse to silent no-match."""

from __future__ import annotations

import os

os.environ.setdefault("SAARTHI_MOCK_EMBEDDING", "1")

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.api.chat import process_chat_request
from app.rag.embeddings import embed
from app.rag.language_detect import detect_language_and_intent, extract_specific_activity
from app.rag.memory import clear_session, get_session_profile
from app.rag.query_context import build_retrieval_query
from app.rag.retriever import reset_store, retrieve_ranked_schemes
from app.rag.scheme_knowledge import load_knowledge_chunks
from app.rag.vector_store import build_store
from app.schemas.chat import ChatProfile, ChatRequest

NSFDC_EDU = "nsfdc-education"
FREE_COACHING = "0070a49e-2e01-554a-8f33-e6ee5648877e"


@pytest.fixture(scope="module")
def rag_store():
    chunks = load_knowledge_chunks()
    store = build_store(chunks, embed)
    reset_store(store)
    yield store
    reset_store(None)


class _FakeLLM:
    def __init__(self, text="advisory reply"):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


def _top(query: str, profile: ChatProfile | None = None):
    spec = build_retrieval_query(query, profile=profile)
    ranked = retrieve_ranked_schemes(
        query=spec.search_text,
        organization_filter=spec.organization_scope,
        domain_filter=spec.domain,
        assistance_type_filter=spec.assistance_type,
        retrieval_query=spec,
        top_k=10,
    )
    return spec, ranked


EDU_QUERIES = [
    ("मुझे पढ़ाई के लिए लोन चाहिए", "hi"),
    ("mujhe padhai ke liye loan chahiye", "hi"),
    ("I need an education loan", "en"),
    ("I need a loan for my studies", "en"),
    ("I need a loan for college", "en"),
    ("I need a student loan", "en"),
    ("मुझे शिक्षा के लिए ऋण चाहिए", "hi"),
    ("मुझे कॉलेज की पढ़ाई के लिए लोन चाहिए", "hi"),
    ("मुझे पढ़ाई के लिए पैसे चाहिए", "hi"),
    ("mujhe education ke liye loan chahiye", "hi"),
    ("mujhe college ki padhai ke liye loan chahiye", "hi"),
]


@pytest.mark.parametrize("query,lang", EDU_QUERIES)
def test_education_queries_retrieve_education_loan(rag_store, query, lang):
    det = detect_language_and_intent(query)
    assert det.intent == "EDUCATION_LOAN"
    assert det.domain == "EDUCATION"
    spec, ranked = _top(query)
    assert spec.domain == "EDUCATION"
    assert spec.assistance_type == "LOAN"
    assert ranked
    assert ranked[0].scheme_id == NSFDC_EDU
    assert ranked[0].organization == "NSFDC"
    assert ranked[0].assistance_type == "LOAN"
    ids = {s.scheme_id for s in ranked}
    names = " ".join(s.scheme_name.lower() for s in ranked)
    assert FREE_COACHING not in ids
    assert "scholarship" not in names
    assert "coach" not in names


def test_education_query_not_stuck_in_agriculture_profile(rag_store):
    prior = ChatProfile(projectType="AGRICULTURE", activity="CROP_FARMING", estimatedProjectCost=200000)
    spec, ranked = _top("मुझे पढ़ाई के लिए लोन चाहिए", prior)
    assert spec.domain == "EDUCATION"
    assert ranked and ranked[0].scheme_id == NSFDC_EDU


def test_crop_farming_is_not_rice_or_dairy(rag_store):
    for query in (
        "mujhe fasal ki kheti keliye loan chaiye",
        "मुझे फसल की खेती के लिए लोन चाहिए",
    ):
        det = detect_language_and_intent(query)
        assert det.domain == "AGRICULTURE"
        assert extract_specific_activity(query) == "CROP_FARMING"
        spec, ranked = _top(query)
        assert spec.domain == "AGRICULTURE"
        assert spec.activity == "CROP_FARMING"
        assert ranked and ranked[0].scheme_id == "nsfdc-term-loan"
        assert extract_specific_activity(query) != "RICE_FARMING"
        assert extract_specific_activity(query) != "DAIRY_FARMING"


def test_rice_dairy_farming_unchanged(rag_store):
    assert extract_specific_activity("Rice farming") == "RICE_FARMING"
    assert extract_specific_activity("Dairy farming") == "DAIRY_FARMING"
    assert extract_specific_activity("Farming") is None
    rice = detect_language_and_intent("Rice farming")
    assert rice.domain == "AGRICULTURE"
    farm = detect_language_and_intent("Farming")
    assert farm.domain == "AGRICULTURE"
    assert farm.activity is None


def test_guided_hindi_education_names_retrieved_scheme(rag_store):
    session = "sess-edu-live-hi"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("no verified NSFDC scheme")):
        resp = process_chat_request(
            ChatRequest(
                query="मुझे पढ़ाई के लिए लोन चाहिए",
                language="hi",
                conversation_id=session,
                guideMe=True,
            )
        )
    text = resp.answer or ""
    assert "गढ़ नहीं" not in text
    assert "Educational Loan" in text or "शैक्षिक" in text or "nsfdc-education" in text.lower()
    if "scholarship" in text.lower():
        assert "ऋण उत्पाद नहीं" in text or "not a loan" in text.lower() or "not loan" in text.lower()
    assert resp.related_scheme_ids
    assert NSFDC_EDU in resp.related_scheme_ids


def test_guided_education_llm_disabled_still_uses_retrieval(rag_store):
    session = "sess-edu-fallback"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(
            ChatRequest(
                query="I need an education loan",
                language="en",
                conversation_id=session,
                guideMe=True,
            )
        )
    assert "Educational Loan" in (resp.answer or "")
    assert NSFDC_EDU in (resp.related_scheme_ids or [])


def test_agri_then_education_does_not_keep_no_match(rag_store):
    session = "sess-switch-edu"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("advisory reply")):
        process_chat_request(
            ChatRequest(
                query="mujhe fasal ki kheti keliye loan chaiye",
                language="hi",
                conversation_id=session,
                guideMe=True,
            )
        )
        process_chat_request(
            ChatRequest(
                query="2 lakh",
                language="hi",
                conversation_id=session,
                guideMe=True,
            )
        )
        resp = process_chat_request(
            ChatRequest(
                query="मुझे पढ़ाई के लिए लोन चाहिए",
                language="hi",
                conversation_id=session,
                guideMe=True,
            )
        )
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert "गढ़ नहीं" not in (resp.answer or "")
    assert NSFDC_EDU in (resp.related_scheme_ids or []) or "Educational Loan" in (resp.answer or "")
