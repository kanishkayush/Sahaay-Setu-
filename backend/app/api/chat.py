import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatResponse, ResponseSource
from app.schemas.explanation import GroundingStatus
from app.rag.retriever import retrieve
from app.rag.chat_service import generate_chat_answer
import app.rag.memory as memory
from app.rag.language_detect import detect_language_and_intent, resolve_conversation_language

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

        # Conversation language lives on the session. The request language field
        # is only an app hint — short tokens like "BTech" / "Jaipur" / "2 lakh"
        # must not switch the conversation just because they use Latin letters.
        prior_language = None
        if request.conversation_id:
            prior_language = memory.get_session_profile(request.conversation_id).preferredLanguage
        request.language = resolve_conversation_language(
            request.query,
            prior=prior_language,
            app_hint=request.language,
        )
        if request.conversation_id:
            session_profile = memory.get_session_profile(request.conversation_id)
            if session_profile.preferredLanguage != request.language:
                session_profile.preferredLanguage = request.language
                memory.update_session_profile(request.conversation_id, session_profile)
        
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
        if request.guideMe and (detection.intent or detection.gender):
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

        # Step 2: Conversation-aware retrieval query (short answers merge into state)
        profile_for_rag = None
        if request.conversation_id:
            profile_for_rag = memory.get_session_profile(request.conversation_id)
        if detection.gender and profile_for_rag is not None and not profile_for_rag.gender:
            profile_for_rag.gender = detection.gender
            memory.update_session_profile(request.conversation_id, profile_for_rag)
        from app.rag.query_context import build_retrieval_query
        retrieval_spec = build_retrieval_query(
            request.query,
            profile=profile_for_rag,
            detection=detection,
            language=request.language,
        )

        if detection.intent == "WOMEN_DISCOVERY" or (
            detection.gender and not detection.intent
        ):
            from app.rag.scheme_advisor import build_brief, ui_cards as adviser_ui_cards, detect_adviser_mode
            mode, named = detect_adviser_mode(request.query)
            brief = build_brief(
                domain=None if detection.intent == "WOMEN_DISCOVERY" else retrieval_spec.domain,
                amount=retrieval_spec.requested_amount,
                activity=retrieval_spec.activity,
                lang=request.language or "en",
                mode=mode,
                named_ids=named,
                income=float(profile_for_rag.annualFamilyIncome) if profile_for_rag and profile_for_rag.annualFamilyIncome is not None else None,
                query=request.query,
                sc_status=profile_for_rag.scEligibilityStatus if profile_for_rag else None,
                gender=detection.gender or (profile_for_rag.gender if profile_for_rag else None),
            )
            return ChatResponse(
                answer=brief.answer,
                language=request.language or "en",
                citations=[],
                ui_cards=adviser_ui_cards(brief, request.language or "en"),
                grounding_status="GROUNDED",
                related_scheme_ids=brief.related_ids,
                response_source=ResponseSource.RAG_LLM,
            )

        # Step 3: Retrieve context (org/domain/assistance filters before ranking)
        retrieval_start = time.time()
        retrieved_chunks = retrieve(
            query=retrieval_spec.search_text,
            scheme_id_filter=request.scheme_id_filter,
            min_similarity=None,
            organization_filter=retrieval_spec.organization_scope,
            domain_filter=retrieval_spec.domain,
            assistance_type_filter=retrieval_spec.assistance_type,
            retrieval_query=retrieval_spec,
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
