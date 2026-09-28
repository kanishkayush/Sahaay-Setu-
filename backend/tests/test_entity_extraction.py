"""Voice/text entity extraction must not invent rice/dairy from generic farming."""

from types import SimpleNamespace
from unittest.mock import patch

from app.api.chat import process_chat_request
from app.rag.language_detect import detect_language_and_intent, extract_specific_activity
from app.rag.memory import clear_session, get_session_profile
from app.schemas.chat import ChatRequest


class _FakeLLM:
    def __init__(self, text="advisory reply"):
        self.choices = [SimpleNamespace(message=SimpleNamespace(content=text))]


def test_extract_specific_activity_evidence_only():
    assert extract_specific_activity("Farming") is None
    assert extract_specific_activity("मुझे खेती के लिए लोन चाहिए") is None
    assert extract_specific_activity("Rice farming") == "RICE_FARMING"
    assert extract_specific_activity("Dairy farming") == "DAIRY_FARMING"
    assert extract_specific_activity("I need a livestock loan") == "LIVESTOCK"
    assert extract_specific_activity("मुझे पशुपालन के लिए लोन चाहिए") == "LIVESTOCK"
    assert extract_specific_activity("मुझे चावल की खेती के लिए लोन चाहिए") == "RICE_FARMING"


def test_farming_detects_agriculture_without_crop():
    d = detect_language_and_intent("Farming")
    assert d.intent == "AGRICULTURE"
    assert d.domain == "AGRICULTURE"
    assert d.activity is None
    assert "rice" not in d.translated_query_en.lower()


def test_kheti_detects_agriculture_without_crop():
    d = detect_language_and_intent("मुझे खेती के लिए लोन चाहिए")
    assert d.intent == "AGRICULTURE"
    assert d.domain == "AGRICULTURE"
    assert d.activity is None


def _chat(query: str, session: str, language: str = "en"):
    clear_session(session)
    req = ChatRequest(query=query, language=language, conversation_id=session, guideMe=True)
    with (
        patch("app.rag.guided_journey.litellm.completion", return_value=_FakeLLM("Could you tell me more?")),
        patch("app.rag.retriever.retrieve", return_value=[]),
    ):
        return process_chat_request(req), get_session_profile(session)


def test_farming_does_not_invent_rice():
    resp, profile = _chat("Farming", "sess-farming", "en")
    text = (resp.answer or "").lower()
    assert "rice" not in text
    assert "चावल" not in (resp.answer or "")
    assert profile.activity is None


def test_farming_fallback_does_not_invent_rice_or_force_term_loan():
    clear_session("sess-farm-fb")
    req = ChatRequest(query="Farming", language="en", conversation_id="sess-farm-fb", guideMe=True)
    with (
        patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")),
        patch("app.rag.retriever.retrieve", return_value=[]),
    ):
        resp = process_chat_request(req)
    text = (resp.answer or "").lower()
    assert "rice" not in text
    assert "dedicated" in text or "catalogue" in text or "could not find" in text
    assert "recommended" not in text
    profile = get_session_profile("sess-farm-fb")
    assert profile.recommendedSchemeId != "nsfdc-term-loan"


def test_rice_farming_sets_rice_activity():
    resp, profile = _chat("Rice farming", "sess-rice", "en")
    assert profile.activity == "RICE_FARMING"


def test_dairy_farming_sets_dairy_activity():
    _, profile = _chat("Dairy farming", "sess-dairy", "en")
    assert profile.activity == "DAIRY_FARMING"


def test_hindi_rice_sets_rice_activity():
    _, profile = _chat("मुझे चावल की खेती के लिए लोन चाहिए", "sess-hi-rice", "hi")
    assert profile.activity == "RICE_FARMING"
