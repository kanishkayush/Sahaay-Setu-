import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatResponse, ResponseSource
from app.schemas.explanation import GroundingStatus
from app.rag.retriever import retrieve
from app.rag.chat_service import generate_chat_answer
import app.rag.memory as memory
from app.rag.language_detect import detect_language_and_intent

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1",
    tags=["chat"],
    responses={404: {"description": "Not found"}},
)

from app.rag.guided_journey import process_guided_journey
from app.schemas.chat import ConversationState

def process_chat_request(request: ChatRequest) -> ChatResponse:
    """
    Core conversational orchestration logic.
    Shared by /v1/chat and /v1/assistant/query endpoints.
    
    Pipeline:
      1. Detect language + intent (deterministic, <1ms)
      2. If already in a guided journey session → continue it
      3. If guideMe and loan intent detected → start guided journey
      4. Otherwise → RAG retrieval + LLM answer generation
    """
    start_time = time.time()
    try:
        # Step 0: Language detection + intent extraction (deterministic, no LLM)
        detection = detect_language_and_intent(request.query)
        
        # Override language ONLY if we successfully detected it, and respect stickiness.
        # RULE: If the user has already established a language preference (request.language is set)
        # and the current query is short (≤3 words) or numeric (like "200000", "2 lakh", "rice"),
        # NEVER override the language — these are contextual answers, not language switches.
        if detection.detected_language:
            has_existing_lang = bool(request.language and request.language != "en")
            is_short_query = len(request.query.strip().split()) <= 4
            # Only upgrade to a detected non-English language, or switch if we don't have one yet.
            if detection.detected_language != "en":
                # Confidently detected as non-English (script-based): always trust this.
                request.language = detection.detected_language
            elif not has_existing_lang and not is_short_query:
                # No prior language and query is long enough to be reliable.
                request.language = detection.detected_language
            # else: keep the existing language preference — short English/neutral words
            # like "rice", "dairy", "200000", "BTech" inside a Hindi session stay Hindi.
        
        normalized_query = detection.translated_query_en
        is_low_info = detection.is_low_info

        # Step 0.5: If already in a guided journey, continue it
        # (This handles follow-up answers like PIN codes, business type, etc.)
        if request.conversation_id:
            profile = memory.get_session_profile(request.conversation_id)
            if profile.conversationState and profile.conversationState != ConversationState.COMPLETED:
                gj_resp = process_guided_journey(request)
                if gj_resp:
                    return gj_resp
                # guided_journey returned None (exception / unhandled state)
                # Do NOT fall through to generic RAG — that produces "मैं सारथी हूँ" mid-conversation.
                # Instead, provide a minimal context-aware reply to keep the conversation going.
                lang = request.language or "en"
                _GJ_RECOVERY_MAP = {
                    "en": "I'm sorry, I didn't quite understand. Could you please rephrase your answer?",
                    "hi": "माफ़ करें, मैं समझ नहीं पाया। क्या आप अपना उत्तर दोबारा बता सकते हैं?",
                    "mr": "माफ करा, मला नीट समजले नाही. तुम्ही तुमचे उत्तर पुन्हा सांगू शकाल का?",
                    "bn": "ক্ষমা করবেন, আমি ঠিকমতো বুঝতে পারিনি। আপনি কি আপনার উত্তর আবার বলতে পারবেন?",
                    "ta": "மன்னிக்கவும், எனக்கு சரியாக புரியவில்லை. உங்கள் பதிலை மீண்டும் சொல்ல முடியுமா?",
                    "te": "క్షమించండి, నాకు సరిగ్గా అర్థం కాలేదు. మీ జవాబును మళ్ళీ చెప్పగలరా?",
                }
                return ChatResponse(
                    answer=_GJ_RECOVERY_MAP.get(lang, _GJ_RECOVERY_MAP["en"]),
                    language=lang,
                    citations=[],
                    grounding_status="GROUNDED",
                    related_scheme_ids=[],
                    response_source=ResponseSource.CLARIFICATION,
                )

        # Step 0.6: If guideMe is requested and we detected a loan intent,
        # start the guided journey — but with intent context
        if request.guideMe and detection.intent:
            # Pass the detected intent to the guided journey so it can
            # provide a conversational RAG-grounded response first
            request._detected_intent = detection.intent
            gj_resp = process_guided_journey(request)
            if gj_resp:
                return gj_resp


        # Step 1: Low-information query guard
        if is_low_info:
            lang = request.language or "en"
            
            clarification_map = {
                "en": "Please tell me what you need financial assistance for, such as education, a small business, dairy farming, transport, or another activity.",
                "hi": "कृपया मुझे बताएं कि आपको किस कार्य के लिए वित्तीय सहायता की आवश्यकता है, जैसे शिक्षा, छोटा व्यवसाय, डेयरी फार्मिंग, परिवहन, या कोई अन्य गतिविधि।",
                "mr": "कृपया मला सांगा की तुम्हाला कोणत्या कार्यासाठी आर्थिक मदतीची आवश्यकता आहे, जसे की शिक्षण, छोटा व्यवसाय, दुग्ध व्यवसाय, वाहतूक किंवा इतर एखादी कृती.",
                "bn": "অনুগ্রহ করে আমাকে বলুন আপনার কীসের জন্য আর্থিক সহায়তার প্রয়োজন, যেমন শিক্ষা, ছোট ব্যবসা, দুগ্ধ খামার, পরিবহন বা অন্য কোনও কাজের জন্য।",
                "ta": "கல்வி, சிறு தொழில், பால் பண்ணை, போக்குவரத்து அல்லது வேறு ஏதேனும் செயல்பாடு போன்ற எதற்கு உங்களுக்கு நிதி உதவி தேவை என்பதை தயவுசெய்து எனக்குத் தெரிவிக்கவும்.",
                "te": "విద్య, చిన్న వ్యాపారం, పాడి పరిశ్రమ, రవాణా లేదా ఇతర కార్యకలాపాల కోసం మీకు ఆర్థిక సహాయం ఎందుకు కావాలో దయచేసి నాకు చెప్పండి."
            }
            answer_text = clarification_map.get(lang, clarification_map["en"])
            
            resp = ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                grounding_status=GroundingStatus.INSUFFICIENT_CONTEXT,
                related_scheme_ids=[],
                response_source=ResponseSource.CLARIFICATION
            )
            logger.info(f"[CHAT] conversation_id={request.conversation_id} language={request.language} query_length={len(request.query)} response_source={resp.response_source.value} total_ms={int((time.time()-start_time)*1000)}")
            return resp

        # Step 2: Context Resolution for Retrieval
        recent_turns = memory.get_recent_turns(request.conversation_id) if request.conversation_id else []
        retrieval_query = normalized_query
        if recent_turns and len(normalized_query.split()) <= 6:
            # If the current query is very short and we have history, prepend the last query for context
            retrieval_query = f"{recent_turns[-1]['query']} {normalized_query}"

        # Step 3: Retrieve context
        retrieval_start = time.time()
        retrieved_chunks = retrieve(
            query=retrieval_query,
            scheme_id_filter=request.scheme_id_filter,
            min_similarity=0.08,
            organization_filter=detection.organization,
            domain_filter=detection.domain,
            assistance_type_filter=detection.assistance_type,
        )
        retrieval_ms = int((time.time() - retrieval_start) * 1000)
        
        # Step 4: Generate grounded answer
        chat_history_str = memory.get_history(request.conversation_id) if request.conversation_id else None
        
        llm_start = time.time()
        response = generate_chat_answer(
            request, 
            retrieved_chunks,
            chat_history=chat_history_str
        )
        llm_ms = int((time.time() - llm_start) * 1000)
        
        # Save to memory
        if request.conversation_id and response.response_source != ResponseSource.DOMAIN_FALLBACK:
            memory.add_turn(request.conversation_id, request.query, response.answer)
            
        total_ms = int((time.time() - start_time) * 1000)
        
        logger.info(
            f"[CHAT] conversation_id={request.conversation_id} "
            f"language={response.language} "
            f"query_length={len(request.query)} "
            f"retrieved_schemes={[c.chunk.scheme_id for c in retrieved_chunks]} "
            f"retrieved_chunks={len(retrieved_chunks)} "
            f"retrieval_ms={retrieval_ms} "
            f"llm_ms={llm_ms} "
            f"total_ms={total_ms} "
            f"response_source={response.response_source.value} "
            f"fallback={response.response_source != ResponseSource.RAG_LLM}"
        )
        
        return response
    except Exception as e:
        logger.exception("Chat logic failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate chat response: {str(e)}"
        )

from fastapi import Header

@router.post("/chat", response_model=ChatResponse)
def chat_endpoint(
    request: ChatRequest,
    x_user_id: str | None = Header(None)
):
    """
    Conversational Multilingual RAG Endpoint.
    
    Accepts a free-form query and optional profile data.
    Retrieves scheme context and returns a grounded conversational answer.
    """
    if x_user_id:
        request.user_id = x_user_id
    return process_chat_request(request)
