import logging
import time
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import ValidationError

from app.schemas.chat import ChatRequest, ChatResponse, ResponseSource
from app.schemas.explanation import GroundingStatus
from app.rag.retriever import retrieve
from app.rag.chat_service import generate_chat_answer
import app.rag.memory as memory

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
    """
    start_time = time.time()
    try:
        # Check if already in a guided journey
        if request.conversation_id:
            profile = memory.get_session_profile(request.conversation_id)
            if profile.conversationState and profile.conversationState != ConversationState.COMPLETED:
                gj_resp = process_guided_journey(request)
                if gj_resp: return gj_resp

        # Check if we should start a new guided journey
        if request.guideMe:
            gj_resp = process_guided_journey(request)
            if gj_resp: return gj_resp

        # Step 1: Low-information query guard
        low_info_words = {"loan", "help", "scheme", "hi", "लोन", "मदद", "योजना", "hello", "कर्ज", "ঋণ", "கடன்", "రుణం"}
        query_stripped = request.query.strip().lower()
        if query_stripped in low_info_words:
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
        retrieval_query = request.query
        if recent_turns and len(request.query.split()) <= 6:
            # If the current query is very short and we have history, prepend the last query for context
            retrieval_query = f"{recent_turns[-1]['query']} {request.query}"

        # Step 3: Retrieve context
        retrieval_start = time.time()
        retrieved_chunks = retrieve(
            query=retrieval_query,
            scheme_id_filter=request.scheme_id_filter,
            min_similarity=0.08
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
            detail="Failed to generate chat response"
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
