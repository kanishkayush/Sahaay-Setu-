"""
app/api/assistant.py
────────────────────
POST /v1/explanations — Grounded Explanation endpoint.

Flow:
    POST /v1/explanations (ExplanationRequest)
        │
        ▼ ApplicantProfile dict
    _map_to_user_profile()          ← reuses router.py mapping helpers
        │
        ▼
    evaluate_all_schemes()          ← eligibility engine (unchanged)
        │
        ▼
    generate_recommendations()      ← recommendation engine (unchanged)
        │
        ▼
    top_recommendation              ← deterministic, immutable
        │
        ├──────────────────────────────────────┐
        ▼                                      ▼
    build_explanation_context()     retrieve_scheme_context(scheme_id)
    (immutable facts dict)          (metadata-only, no semantic query)
        │                                      │
        └──────────────┬───────────────────────┘
                       ▼
               generate_explanation()
               (LiteLLM + Pydantic validation + citation guard)
                       │
                       ▼
               ExplanationResponse (JSON)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.api.mapper import EDUCATION_STATUS_MAP, PROJECT_TYPE_TO_PURPOSE
from app.eligibility_engine import evaluate_all_schemes
from app.rag.explanation_service import generate_explanation
from app.rag.retriever import retrieve_scheme_context
from app.recommendation_engine import generate_recommendations
from app.schemas.explanation import ExplanationRequest, ExplanationResponse

assistant_router = APIRouter(prefix="/v1")


def _map_profile_to_user_profile(profile: dict) -> dict[str, Any]:
    """
    Converts the raw profile dict from ExplanationRequest into a UserProfile dict
    accepted by the eligibility engine.

    Mirrors the mapping logic from router.py _map_to_user_profile() to avoid
    duplicating business logic. Uses the same PROJECT_TYPE_TO_PURPOSE and
    EDUCATION_STATUS_MAP that the recommendation endpoint uses.
    """
    project_type = profile.get("projectType", "")
    purpose = PROJECT_TYPE_TO_PURPOSE.get(project_type)
    is_education = project_type == "EDUCATION"

    education_status_raw = profile.get("educationStatus", "NONE")
    education_status_backend = EDUCATION_STATUS_MAP.get(education_status_raw)

    estimated_cost = float(profile.get("estimatedProjectCost", 0))

    return {
        "language": profile.get("language", "en"),
        "purpose": purpose,
        "family_income_inr": float(profile.get("annualFamilyIncome", 0)),
        "course_cost_inr": estimated_cost if is_education else None,
        "project_cost_inr": estimated_cost if not is_education else None,
        "beneficiary_category_verified": None,
        "education_status": education_status_backend if is_education else None,
    }


@assistant_router.post("/explanations", response_model=ExplanationResponse)
def create_explanation(request: ExplanationRequest) -> ExplanationResponse:
    """
    Generates a grounded, multilingual explanation for the top deterministic
    scheme recommendation.

    The deterministic engines (eligibility + recommendation) are run first.
    Only after their output is fixed does the RAG + LLM layer run.
    The LLM may only explain; it cannot change the recommendation.
    """
    # --- 1. Deterministic layer ---
    try:
        user_profile = _map_profile_to_user_profile(request.profile)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"Invalid profile: {exc}") from exc

    eval_response = evaluate_all_schemes(user_profile)
    ranked = generate_recommendations(eval_response)

    if ranked.top_recommendation is None:
        raise HTTPException(
            status_code=200,
            detail="No eligible schemes found for this profile. Cannot generate explanation.",
        )

    top = ranked.top_recommendation

    # --- 2. Retrieval layer (metadata-only, scheme-scoped) ---
    # Cap at 3 chunks to stay within Sarvam-105b's combined context window.
    # Canonical section order ensures overview → eligibility_criteria → financial_terms
    # are always the first 3 selected.
    retrieved_chunks = retrieve_scheme_context(
        scheme_id=top.scheme_id,
        max_chunks=3,
    )

    # --- 3. Explanation layer ---
    explanation = generate_explanation(
        top=top,
        retrieved_chunks=retrieved_chunks,
        language=request.language,
    )

    return explanation

from fastapi import APIRouter, Header, HTTPException, status
import uuid
import logging

logger = logging.getLogger(__name__)
from app.api.chat import process_chat_request
from app.schemas.chat import ChatRequest, ResponseSource, ChatProfile
from app.schemas.assistant import AssistantQueryRequest, AssistantQueryResponse

@assistant_router.post("/assistant/query", response_model=AssistantQueryResponse)
def assistant_query_adapter(
    request: AssistantQueryRequest,
    x_user_id: str | None = Header(None)
) -> AssistantQueryResponse:
    """
    Adapter for the frontend's Assistant API contract.
    Maps to the canonical ChatRequest and uses shared chat orchestration.
    """
    profile = None
    if request.profileContext:
        profile = ChatProfile(
            annualFamilyIncome=request.profileContext.annualFamilyIncome,
            projectType=request.profileContext.projectType,
            stateCode=request.profileContext.stateCode
        )
    
    # Do not silently infer eligibility. The chat pipeline respects the Profile safety rule.
    chat_request = ChatRequest(
        query=request.query,
        language=request.responseLanguage,
        profile=profile,
        conversation_id=request.sessionId,
        user_id=x_user_id,
        guideMe=request.guideMe
    )

    chat_response = process_chat_request(chat_request)

    if chat_request.language and chat_response.language != chat_request.language:
        logger.error(
            "LANGUAGE CONTRACT VIOLATION: %s request produced %s response",
            chat_request.language, chat_response.language
        )

    grounded = chat_response.grounding_status == "GROUNDED" and chat_response.response_source != ResponseSource.DOMAIN_FALLBACK
    
    raw_expected_field = getattr(chat_response, 'expected_field', None)
    expected_field = raw_expected_field if isinstance(raw_expected_field, str) else None

    return AssistantQueryResponse(
        messageId=str(uuid.uuid4()),
        answer=chat_response.answer,
        answerLanguage=request.responseLanguage,
        detectedQueryLanguage=request.responseLanguage,
        citations=chat_response.citations,
        suggestedActions=[],
        uiCards=[card.model_dump(exclude_none=True) if hasattr(card, 'model_dump') else card for card in getattr(chat_response, 'ui_cards', [])],
        followUpQuestions=[],
        grounded=grounded,
        sessionId=request.sessionId,
        expectedField=expected_field
    )

import os
import base64
import requests
from app.schemas.assistant import TranscriptionRequest, TranscriptionResponse

@assistant_router.post("/assistant/transcribe", response_model=TranscriptionResponse)
def transcribe_audio(request: TranscriptionRequest) -> TranscriptionResponse:
    """
    Backend STT proxy. Accepts base64 audio from the frontend, sends it to 
    Sarvam AI (or fallback), and returns the transcript.
    """
    sarvam_api_key = os.getenv("SARVAM_API_KEY", "")
    
    try:
        audio_bytes = base64.b64decode(request.audioBase64)
        
        if not sarvam_api_key or sarvam_api_key == "test":
            # Mock response for local development when no real key is provided
            fallback_text = "This is a fallback transcription from the backend."
            if request.language == "hi":
                fallback_text = "मुझे डेयरी फार्मिंग के लिए लोन चाहिए।"
            return TranscriptionResponse(
                text=fallback_text,
                detectedLanguage=request.language or "en",
                confidence=0.9
            )
            
        url = "https://api.sarvam.ai/speech-to-text"
        headers = {"api-subscription-key": sarvam_api_key}
        files = {'file': ('audio.wav', audio_bytes, request.mimeType)}
        
        # Sarvam typically expects 'language_code' like 'hi-IN' or 'en-IN'
        lang_map = {"hi": "hi-IN", "en": "en-IN", "mr": "mr-IN", "bn": "bn-IN", "ta": "ta-IN", "te": "te-IN"}
        lang_code = lang_map.get(request.language, "hi-IN") if request.language else "hi-IN"
        
        data = {'language_code': lang_code}
        
        res = requests.post(url, files=files, data=data, headers=headers, timeout=15)
        res.raise_for_status()
        
        result = res.json()
        return TranscriptionResponse(
            text=result.get("transcript", ""),
            detectedLanguage=request.language,
            confidence=0.95
        )
    except Exception as e:
        print(f"Transcription error: {e}")
        # Return empty string instead of failing, to let the UI handle it gracefully
        return TranscriptionResponse(text="")
