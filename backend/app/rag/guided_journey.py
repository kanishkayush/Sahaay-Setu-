import json
import os
import uuid
from typing import Dict, Any, List, Optional

import litellm

from app.schemas.chat import ChatRequest, ChatResponse, ChatProfile, ConversationState, ResponseSource
from app.schemas.assistant import AssistantUICard, AssistantUICardType
from app.rag.memory import get_history, get_session_profile, update_session_profile, add_turn
from app.eligibility_engine import evaluate_all_schemes
from app.recommendation_engine import generate_recommendations
from app.services.storage import get_profile_store

def _llm_model() -> str:
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL environment variable is not set.")
    return model

def process_guided_journey(request: ChatRequest) -> ChatResponse:
    """
    Main state machine for the guided loan assistant.
    """
    session_id = request.conversation_id or str(uuid.uuid4())
    
    # Merge any frontend-provided profile context into memory
    if request.profile:
        update_session_profile(session_id, request.profile)
        
    profile = get_session_profile(session_id)
    
    # -----------------------------------------------------------------------
    # Phase 2: Seeding ChatProfile from PersistentUserProfile
    # -----------------------------------------------------------------------
    if request.user_id:
        store = get_profile_store()
        persistent = store.get(request.user_id)
        if persistent:
            print(f"[PROFILE] Loaded profile for user: {request.user_id}")
            # Ensure fullName uses the same schema
            # We don't have fullName in ChatProfile explicitly yet, but we will add it to schemas/chat.py if needed.
            # Actually, ChatProfile might not have fullName. Let's set it if it exists.
            if persistent.get("fullName") and not getattr(profile, "fullName", None):
                setattr(profile, "fullName", persistent.get("fullName"))
                
            address = persistent.get("address", {})
            if address.get("pinCode") and not profile.pinCode:
                profile.pinCode = address.get("pinCode")
                print(f"[GUIDED JOURNEY] Seeded pinCode from persistent profile: {profile.pinCode}")
                
            update_session_profile(session_id, profile)
    
    state = profile.conversationState or ConversationState.INITIAL_QUERY
    
    try:
        # Simple state transition logic
        if state == ConversationState.INITIAL_QUERY:
            return _handle_initial_query(request, profile, session_id)
            
        if state == ConversationState.COLLECTING_ELIGIBILITY:
            return _handle_collecting_eligibility(request, profile, session_id)
            
        if state == ConversationState.SCHEME_RECOMMENDATION:
            return _handle_scheme_recommendation(request, profile, session_id)
            
        if state == ConversationState.DOCUMENT_PREPARATION:
            return _handle_document_preparation(request, profile, session_id)
            
        if state == ConversationState.PARTNER_SEARCH:
            return _handle_partner_search(request, profile, session_id)
    except Exception as e:
        print(f"Error in process_guided_journey: {e}")

    # Fallback to standard RAG if state is not matched or an error occurs
    return None

def _deterministic_intent_extraction(query: str) -> Optional[dict]:
    query_lower = query.lower()
    
    # Is it asking for a loan?
    loan_keywords = ["loan", "लोन", "ऋण", "कर्ज", "finance", "financing", "money", "funding", "capital", "start", "expand", "run", "business", "व्यवसाय"]
    is_loan = any(kw in query_lower for kw in loan_keywords)
    
    if not is_loan:
        return None
        
    # Check for specific activities
    ACTIVITY_ALIASES = {
        "DAIRY_FARMING": [
            "dairy farming",
            "dairy farm",
            "milk business",
            "डेयरी फार्म",
            "डेयरी फार्मिंग",
            "दूध का व्यवसाय",
            "पशुपालन",
            "dairy"
        ],
        "POULTRY": ["poultry", "murgi", "मुर्गी"],
        "TAILORING": ["tailor", "silai", "सिलाई"],
        "SHOP": ["shop", "dukan", "दुकान", "store"],
        "EDUCATION_LOAN": [
            "education", "study", "studies", "college", "school", "btech", "degree", "course", 
            "पढ़ाई", "शिक्षा", "कॉलेज", "student", "mba", "masters", "phd", 
            "bachelors", "graduation", "university", "institute", "fees", "higher education",
            "padhai", "shiksha", "paddhai"
        ],
        "GENERAL_BUSINESS": [
            "business", "startup", "company", "enterprise", "manufacturing", "व्यापार", "बिज़नेस", 
            "handicraft", "craft", "artisan", "weaving", "pottery", "हस्तशिल्प", "शिल्प", "कारीगर",
            "vyapar", "bijnes", "karkhana", "dukaan"
        ]
    }
    
    for activity, aliases in ACTIVITY_ALIASES.items():
        if any(alias in query_lower for alias in aliases):
            return {"intent": "LOAN", "activity": activity}
            
    return None

def _handle_initial_query(request: ChatRequest, profile: ChatProfile, session_id: str) -> ChatResponse:
    """
    Handle the initial user query with a CONVERSATIONAL RAG-grounded response.
    
    Instead of immediately jumping to form-filling, this:
    1. Detects intent (deterministic first, LLM fallback)
    2. Retrieves relevant scheme context via RAG
    3. Generates a natural conversational response acknowledging the intent
    4. Sets up the guided journey state for follow-up questions
    """
    from app.rag.language_detect import detect_language_and_intent
    
    # Check if intent was already detected by chat.py
    pre_detected_intent = getattr(request, '_detected_intent', None)
    
    # Deterministic check
    data = _deterministic_intent_extraction(request.query)
    
    # Merge pre-detected intent if deterministic extraction didn't find one
    if not data and pre_detected_intent:
        intent_to_activity = {
            "EDUCATION_LOAN": "EDUCATION_LOAN",
            "AGRICULTURE": "DAIRY_FARMING",  
            "BUSINESS": "GENERAL_BUSINESS",
            "GENERAL_LOAN": None,
        }
        activity = intent_to_activity.get(pre_detected_intent)
        if activity:
            data = {"intent": "LOAN", "activity": activity}
        elif pre_detected_intent == "GENERAL_LOAN":
            data = {"intent": "AMBIGUOUS_LOAN"}
    
    if data:
        if data.get("intent") == "AMBIGUOUS_LOAN":
            lang = request.language or "en"
            clarification_map = {
                "en": "I can help you find the right financial assistance. Could you tell me what you need the loan for — education, a small business, dairy farming, or another activity?",
                "hi": "मैं आपको सही वित्तीय सहायता खोजने में मदद कर सकता हूँ। कृपया बताएं कि आपको किसलिए लोन चाहिए — पढ़ाई, छोटा व्यवसाय, डेयरी फार्मिंग, या कोई अन्य कार्य?",
                "mr": "मी तुम्हाला योग्य आर्थिक मदत शोधण्यात मदत करू शकतो. कृपया सांगा की तुम्हाला कशासाठी कर्ज हवे आहे — शिक्षण, छोटा व्यवसाय, दुग्ध व्यवसाय किंवा इतर कार्य?",
                "bn": "আমি আপনাকে সঠিক আর্থিক সহায়তা খুঁজে পেতে সাহায্য করতে পারি। অনুগ্রহ করে বলুন আপনার কীসের জন্য ঋণ দরকার — শিক্ষা, ছোট ব্যবসা, দুগ্ধ খামার, বা অন্য কিছু?",
                "ta": "சரியான நிதி உதவியைக் கண்டறிய நான் உங்களுக்கு உதவ முடியும். கடன் எதற்கு வேண்டும் என்று சொல்லுங்கள் — கல்வி, சிறு தொழில், பால் பண்ணை, அல்லது வேறு ஏதேனும்?",
                "te": "సరైన ఆర్థిక సహాయం కనుగొనడంలో నేను మీకు సహాయపడగలను. దయచేసి మీకు రుణం ఎందుకు కావాలో చెప్పండి — విద్య, చిన్న వ్యాపారం, పాడి పరిశ్రమ, లేదా ఇతరం?"
            }
            answer_text = clarification_map.get(lang, clarification_map["en"])
            return ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                grounding_status="GROUNDED",
                related_scheme_ids=[],
                response_source=ResponseSource.CLARIFICATION
            )
        elif data.get("intent") == "LOAN":
            activity = data.get("activity")
            profile.activity = activity
            activity_lower = str(activity).lower() if activity else ""
            
            # Detect education intent
            is_education = (
                activity == "EDUCATION_LOAN" or 
                any(kw in activity_lower for kw in [
                    "education", "study", "padhai", "shiksha", "college",
                    "school", "degree", "course", "student", "btech", "mtech",
                    "bca", "mca", "mbbs", "medical", "engineering", "iti",
                    "diploma", "nursing", "pharmacy", "10th", "12th", "b.tech", "mba", "ba", "bsc", "bcom"
                ])
            )
            if is_education:
                profile.projectType = "EDUCATION"
            
            # ── KEY FIX: Provide a conversational RAG-grounded first response ──
            # Instead of immediately asking for PIN code, give the user
            # relevant scheme information and THEN transition to collection.
            
            lang = request.language or "en"
            
            # Retrieve relevant scheme context
            from app.rag.retriever import retrieve
            
            # Build a retrieval query that matches the intent
            if is_education:
                retrieval_query = "education loan scheme for students college course fees"
                domain = "EDUCATION"
            elif any(kw in activity_lower for kw in ["dairy", "farm", "agriculture", "kheti", "pashupalan"]):
                retrieval_query = "agriculture farming dairy loan scheme self-employment"
                domain = "AGRICULTURE"
            else:
                retrieval_query = "business loan scheme self-employment enterprise"
                domain = "BUSINESS"
            
            retrieved_chunks = retrieve(
                query=retrieval_query, 
                top_k=3, 
                min_similarity=0.05,
                domain_filter=domain,
                assistance_type_filter="LOAN"
            )
            
            # Build a natural first response using the retrieved context
            answer_text = _build_conversational_first_response(
                activity=activity,
                is_education=is_education,
                retrieved_chunks=retrieved_chunks,
                lang=lang,
                user_query=request.query,
            )
            
            # Set up the guided journey state
            profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
            update_session_profile(session_id, profile)
            
            # Save this turn to memory
            add_turn(session_id, request.query, answer_text)
            
            return ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                grounding_status="GROUNDED",
                related_scheme_ids=[rc.chunk.scheme_id for rc in retrieved_chunks[:3]],
                response_source=ResponseSource.RAG_LLM,
                expected_field="general"  # No specific field yet — just conversational
            )
    
    # LLM fallback for ambiguous queries
    system_prompt = f"""You are SAARTHI, a scheme advisory assistant.
Determine if the user's query is explicitly asking for a LOAN or FINANCIAL CREDIT for a specific business, education, or activity (e.g., dairy farming, poultry, new business, education loan).
If the user is asking for a scholarship, grant, skill training, or general support, it is NOT a loan.
If yes (it is a loan), you MUST return exactly this JSON object:
{{"intent": "LOAN", "activity": "<ACTIVITY>"}}
If no, return exactly this JSON object:
{{"intent": "GENERAL"}}
Do not include any other text.
"""
    try:
        model = _llm_model()
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": request.query}
            ],
            temperature=0.1
        )
        
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        
        if data.get("intent") == "LOAN":
            activity = data.get("activity")
            profile.activity = activity
            activity_lower = str(activity).lower() if activity else ""
            is_education = any(kw in activity_lower for kw in [
                "education", "study", "padhai", "shiksha", "college",
                "school", "degree", "course", "student", "btech", "mtech",
                "bca", "mca", "mbbs", "medical", "engineering", "iti",
                "diploma", "nursing", "pharmacy", "10th", "12th", "b.tech", "mba", "ba", "bsc", "bcom"
            ])
            if is_education:
                profile.projectType = "EDUCATION"
            
            lang = request.language or "en"
            
            from app.rag.retriever import retrieve
            if is_education:
                retrieval_query = "education loan scheme for students college course fees"
                domain = "EDUCATION"
            else:
                retrieval_query = f"{activity or 'business'} loan scheme self-employment"
                domain = "BUSINESS"
            
            retrieved_chunks = retrieve(
                query=retrieval_query, 
                top_k=3, 
                min_similarity=0.05,
                domain_filter=domain,
                assistance_type_filter="LOAN"
            )
            
            answer_text = _build_conversational_first_response(
                activity=activity,
                is_education=is_education,
                retrieved_chunks=retrieved_chunks,
                lang=lang,
                user_query=request.query,
            )
            
            profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
            update_session_profile(session_id, profile)
            add_turn(session_id, request.query, answer_text)
            
            return ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                grounding_status="GROUNDED",
                related_scheme_ids=[rc.chunk.scheme_id for rc in retrieved_chunks[:3]],
                response_source=ResponseSource.RAG_LLM,
                expected_field="general"
            )
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"Error parsing initial query intent via LLM: {e}")
        
    # If not a loan intent, use standard RAG (route back to standard chat)
    return None


def _build_conversational_first_response(
    activity: str | None,
    is_education: bool,
    retrieved_chunks: list,
    lang: str,
    user_query: str,
) -> str:
    """
    Generate a natural, conversational first response that includes
    relevant scheme information from RAG, rather than immediately
    jumping to form-filling.
    
    Uses the LLM to produce a natural response grounded in retrieved context.
    """
    # Build context from retrieved chunks
    context_parts = []
    for rc in retrieved_chunks[:3]:
        context_parts.append(f"Scheme: {rc.chunk.scheme_name} ({rc.chunk.scheme_id})\n{rc.chunk.text}")
    context_text = "\n\n---\n\n".join(context_parts) if context_parts else "No specific scheme context available."
    
    lang_names = {
        "en": "English", "hi": "Hindi", "mr": "Marathi",
        "bn": "Bengali", "ta": "Tamil", "te": "Telugu"
    }
    lang_name = lang_names.get(lang, "English")
    
    if is_education:
        purpose_desc = "education/studies"
    elif activity:
        purpose_desc = activity.lower().replace("_", " ")
    else:
        purpose_desc = "business/self-employment"
    
    system_prompt = f"""You are SAARTHI, a friendly multilingual loan assistant.
The user wants help with {purpose_desc}.

Here is verified scheme information that may be relevant:
{context_text}

Generate a NATURAL, CONVERSATIONAL response in {lang_name} that:
1. Acknowledges what the user wants (e.g., "Sure, I can help you with education loans")
2. Briefly mentions 1-2 relevant schemes from the context above (name, basic purpose, loan range if available)
3. Asks ONE natural follow-up question to understand their needs better

Rules:
- Be warm and conversational, NOT robotic
- Do NOT use internal field names like existingBusiness, estimatedProjectCost
- Do NOT list every scheme — just the most relevant 1-2
- If the user asked about education, do NOT ask about business type
- If the user asked about farming/agriculture, mention relevant schemes
- Keep it concise (3-5 sentences maximum)
- Respond ENTIRELY in {lang_name}
- Do NOT output JSON
- Do NOT say "based on retrieved context" or mention internal processes

For education queries, ask about the course/program.
For business queries, ask about the type of business/activity.
For agriculture queries, ask about the specific farming activity.
"""
    
    try:
        model = _llm_model()
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ],
            temperature=0.3,
            max_tokens=512,
        )
        answer = (response.choices[0].message.content or "").strip()
        if answer:
            return answer
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"LLM first response generation failed: {e}")
    
    # Deterministic fallback if LLM fails
    fallback_map = {
        "en": {
            "education": "I can help you with education loans. NSFDC offers an Educational Loan Scheme for professional and technical courses. Could you tell me which course or program you're planning to pursue?",
            "agriculture": "I can help you find financing for farming and agriculture. There are several schemes available for agricultural activities. Could you tell me more about what type of farming you're planning?",
            "business": "I can help you with business financing. NSFDC offers several schemes like Micro Finance, Term Loan, and Laghu Vyavsay Yojana for different business sizes. What kind of business are you planning?",
        },
        "hi": {
            "education": "बिल्कुल, मैं आपको शिक्षा ऋण में मदद कर सकता हूँ। NSFDC की शैक्षिक ऋण योजना व्यावसायिक और तकनीकी कोर्स के लिए उपलब्ध है। आप कौन सा कोर्स या प्रोग्राम करना चाहते हैं?",
            "agriculture": "मैं आपको खेती और कृषि के लिए वित्तीय सहायता खोजने में मदद कर सकता हूँ। कई योजनाएं उपलब्ध हैं। आप किस प्रकार की खेती की योजना बना रहे हैं?",
            "business": "मैं आपको व्यवसाय के लिए वित्तीय सहायता में मदद कर सकता हूँ। NSFDC की कई योजनाएं हैं जैसे माइक्रो फाइनेंस, टर्म लोन, और लघु व्यवसाय योजना। आप किस प्रकार का व्यवसाय शुरू करना चाहते हैं?",
        },
        "mr": {
            "education": "नक्कीच, मी तुम्हाला शैक्षणिक कर्जामध्ये मदत करू शकतो. कोणत्या कोर्ससाठी तुम्ही विचार करत आहात?",
            "agriculture": "मी तुम्हाला शेती आणि कृषीसाठी आर्थिक मदत शोधण्यात मदत करू शकतो. तुम्ही कोणत्या प्रकारची शेती करणार आहात?",
            "business": "मी तुम्हाला व्यवसायासाठी आर्थिक मदतीत मदत करू शकतो. तुम्ही कोणता व्यवसाय सुरू करणार आहात?"
        },
        "bn": {
            "education": "আমি আপনাকে শিক্ষা ঋণের বিষয়ে সাহায্য করতে পারি। আপনি কোন কোর্সটি করতে চান?",
            "agriculture": "আমি আপনাকে চাষাবাদের জন্য আর্থিক সহায়তা খুঁজে পেতে সাহায্য করতে পারি। আপনি কি ধরণের চাষাবাদ করতে চান?",
            "business": "আমি আপনাকে ব্যবসার জন্য আর্থিক সহায়তা পেতে সাহায্য করতে পারি। আপনি কি ধরণের ব্যবসা শুরু করতে চান?"
        },
        "ta": {
            "education": "நான் உங்களுக்கு கல்வி கடன்களுக்கு உதவ முடியும். நீங்கள் எந்த படிப்பை படிக்க விரும்புகிறீர்கள்?",
            "agriculture": "விவசாயத்திற்கான நிதி உதவியைக் கண்டறிய நான் உங்களுக்கு உதவ முடியும். நீங்கள் என்ன வகையான விவசாயம் செய்ய திட்டமிட்டுள்ளீர்கள்?",
            "business": "வணிக நிதிக்கு நான் உங்களுக்கு உதவ முடியும். நீங்கள் என்ன வகையான வணிகத்தைத் தொடங்க திட்டமிட்டுள்ளீர்கள்?"
        },
        "te": {
            "education": "నేను మీకు విద్యా రుణాలతో సహాయం చేయగలను. మీరు ఏ కోర్సు చదవాలనుకుంటున్నారు?",
            "agriculture": "వ్యవసాయం కోసం ఆర్థిక సహాయాన్ని కనుగొనడంలో నేను మీకు సహాయం చేయగలను. మీరు ఏ రకమైన వ్యవసాయం చేయాలనుకుంటున్నారు?",
            "business": "వ్యాపార ఆర్థిక సహాయంతో నేను మీకు సహాయం చేయగలను. మీరు ఏ రకమైన వ్యాపారాన్ని ప్రారంభించాలనుకుంటున్నారు?"
        }
    }
    
    category = "education" if is_education else ("agriculture" if activity and any(kw in str(activity).lower() for kw in ["dairy", "farm", "agriculture", "kheti"]) else "business")
    lang_fallbacks = fallback_map.get(lang, fallback_map.get("en", {}))
    return lang_fallbacks.get(category, lang_fallbacks.get("business", "I can help you find suitable loan schemes. Could you tell me more about what you need?"))

def _handle_collecting_eligibility(request: ChatRequest, profile: ChatProfile, session_id: str, is_transition: bool = False) -> ChatResponse:
    # If this is not a direct transition, we need to extract the user's answer from their query
    if not is_transition:
        _extract_profile_data_from_query(request.query, profile, session_id, request.user_id)
        # Update session profile with extracted data before checking missing fields
        update_session_profile(session_id, profile)
        
    # ── Resolve short one-word activity answers BEFORE checking missing fields ──
    # If activity is still vague and user just answered, try to refine it from the query.
    _VAGUE_ACTIVITIES = {"BUSINESS", "AGRICULTURE", "GENERAL_BUSINESS", "FARMING", "GENERAL", None}
    _ACTIVITY_SHORT_MAP = {
        # Agriculture / Allied
        "rice": "RICE_FARMING", "paddy": "RICE_FARMING", "धान": "RICE_FARMING",
        "wheat": "WHEAT_FARMING", "गेहूं": "WHEAT_FARMING", "gehun": "WHEAT_FARMING",
        "vegetable": "VEGETABLE_FARMING", "vegetables": "VEGETABLE_FARMING",
        "सब्जी": "VEGETABLE_FARMING", "sabji": "VEGETABLE_FARMING",
        "fruit": "HORTICULTURE", "fruits": "HORTICULTURE", "फल": "HORTICULTURE", "horticulture": "HORTICULTURE",
        "dairy": "DAIRY_FARMING", "milk": "DAIRY_FARMING", "डेयरी": "DAIRY_FARMING", "दूध": "DAIRY_FARMING",
        "poultry": "POULTRY", "murgi": "POULTRY", "मुर्गी": "POULTRY",
        "fish": "FISHERY", "fishing": "FISHERY", "मछली": "FISHERY",
        "goat": "GOAT_REARING", "sheep": "GOAT_REARING", "बकरी": "GOAT_REARING",
        "pig": "PIG_REARING", "सूअर": "PIG_REARING",
        # Business / Trade
        "shop": "SMALL_RETAIL", "dukaan": "SMALL_RETAIL", "दुकान": "SMALL_RETAIL",
        "tailoring": "TAILORING", "silai": "TAILORING", "सिलाई": "TAILORING",
        "handicraft": "HANDICRAFT", "craft": "HANDICRAFT", "हस्तशिल्प": "HANDICRAFT",
        "beauty": "BEAUTY_PARLOUR", "salon": "BEAUTY_PARLOUR",
        "transport": "TRANSPORT", "auto": "TRANSPORT", "cab": "TRANSPORT",
        "repair": "REPAIR_WORKSHOP", "mechanic": "REPAIR_WORKSHOP",
        "catering": "CATERING", "food": "FOOD_PROCESSING",
    }
    if profile.activity in _VAGUE_ACTIVITIES and not is_transition:
        q_low = request.query.strip().lower()
        for kw, mapped in _ACTIVITY_SHORT_MAP.items():
            if kw in q_low:
                profile.activity = mapped
                update_session_profile(session_id, profile)
                print(f"[Guided] Resolved short activity answer '{kw}' → {mapped}")
                break

    # Check what is missing
    missing_fields = []
    if profile.pinCode is None and (profile.stateCode is None or profile.districtCode is None):
        missing_fields.append("PIN Code")
    elif profile.projectType != "EDUCATION" and (profile.activity is None or profile.activity in _VAGUE_ACTIVITIES):
        missing_fields.append("Specific Activity")
    elif profile.projectType != "EDUCATION" and profile.existingBusiness is None:
        missing_fields.append("Is this a new business or an existing business?")
    elif profile.estimatedProjectCost is None:
        if profile.projectType == "EDUCATION":
            missing_fields.append("Course Fee")
        else:
            missing_fields.append("Estimated Project Cost")
        
    if not missing_fields:
        # We have everything, move to recommendation
        profile.conversationState = ConversationState.SCHEME_RECOMMENDATION
        update_session_profile(session_id, profile)
        return _handle_scheme_recommendation(request, profile, session_id, is_transition=True)
        
    # Ask the FIRST missing field
    next_question = missing_fields[0]
    
    lang = request.language or "en"
    questions_map = {
        "en": {
            "Specific Activity": "Could you tell me what specific kind of work or farming you want to do?",
            "PIN Code": "I need your 6-digit PIN code to find accurate schemes and partners. Please update your PIN in your Profile.",
            "Is this a new business or an existing business?": "Is this a new business or an existing business?",
            "Estimated Project Cost": "What is the estimated total project cost?",
            "Course Fee": "What is the total estimated course fee?"
        },
        "hi": {
            "Specific Activity": "आप किस प्रकार का काम या खेती शुरू करना चाहते हैं?",
            "PIN Code": "सटीक योजनाएं और भागीदार खोजने के लिए मुझे आपके 6 अंकों के पिन कोड की आवश्यकता है। कृपया अपने प्रोफाइल में अपना पिन अपडेट करें।",
            "Is this a new business or an existing business?": "क्या यह नया व्यवसाय है या आपका पहले से चल रहा व्यवसाय है?",
            "Estimated Project Cost": "इस परियोजना की अनुमानित कुल लागत कितनी है?",
            "Course Fee": "कोर्स की अनुमानित कुल फीस कितनी है?"
        },
        "mr": {
            "Specific Activity": "तुम्हाला कोणता विशिष्ट प्रकारचा व्यवसाय किंवा शेती करायची आहे?",
            "PIN Code": "अचूक योजना आणि भागीदार शोधण्यासाठी मला तुमचा 6-अंकी पिन कोड आवश्यक आहे. कृपया तुमच्या प्रोफाइलमध्ये तुमचा पिन अपडेट करा.",
            "Is this a new business or an existing business?": "हा नवीन व्यवसाय आहे की जुना?",
            "Estimated Project Cost": "अंदाजित प्रकल्प खर्च किती आहे?",
            "Course Fee": "कोर्सची अंदाजित एकूण फी किती आहे?"
        },
        "bn": {
            "Specific Activity": "আপনি নির্দিষ্ট কি ধরনের কাজ বা চাষাবাদ করতে চান তা কি বলতে পারবেন?",
            "PIN Code": "সঠিক স্কিম এবং পার্টনার খুঁজে পেতে আমার আপনার ৬-সংখ্যার পিন কোড দরকার। অনুগ্রহ করে আপনার প্রোফাইলে পিন আপডেট করুন।",
            "Is this a new business or an existing business?": "এটি কি একটি নতুন ব্যবসা না বিদ্যমান ব্যবসা?",
            "Estimated Project Cost": "আনুমানিক প্রকল্প ব্যয় কত?",
            "Course Fee": "কোর্সের আনুমানিক মোট ফি কত?"
        },
        "ta": {
            "Specific Activity": "நீங்கள் எந்த வகையான குறிப்பிட்ட வேலை அல்லது விவசாயம் செய்ய விரும்புகிறீர்கள் என்பதை என்னிடம் கூற முடியுமா?",
            "PIN Code": "சரியான திட்டங்கள் மற்றும் கூட்டாளர்களைக் கண்டறிய உங்கள் 6 இலக்க பின் குறியீடு எனக்குத் தேவை. தயவுசெய்து உங்கள் சுயவிவரத்தில் உங்கள் பின்னைப் புதுப்பிக்கவும்.",
            "Is this a new business or an existing business?": "இது புதிய தொழிலா அல்லது ஏற்கனவே உள்ள தொழிலா?",
            "Estimated Project Cost": "மதிப்பிடப்பட்ட திட்ட செலவு என்ன?",
            "Course Fee": "மதிப்பிடப்பட்ட மொத்த பாட கட்டணம் என்ன?"
        },
        "te": {
            "Specific Activity": "మీరు ఏ నిర్దిష్ట రకమైన పని లేదా వ్యవసాయం చేయాలనుకుంటున్నారో నాకు చెప్పగలరా?",
            "PIN Code": "ఖచ్చితమైన పథకాలు మరియు భాగస్వాములను కనుగొనడానికి నాకు మీ 6-అంకెల పిన్ కోడ్ కావాలి. దయచేసి మీ ప్రొఫైల్‌లో మీ పిన్‌ను అప్‌డేట్ చేయండి.",
            "Is this a new business or an existing business?": "ఇది కొత్త వ్యాపారమా లేదా ఉన్న వ్యాపారమా?",
            "Estimated Project Cost": "అంచనా ప్రాజెక్ట్ వ్యయం ఎంత?",
            "Course Fee": "అంచనా వేసిన మొత్తం కోర్సు ఫీజు ఎంత?"
        }
    }
    
    lang_map = questions_map.get(lang, questions_map["en"])
    answer_text = lang_map.get(next_question, f"Please provide your {next_question}.")
    
    if next_question == "Is this a new business or an existing business?" and profile.pinCode and is_transition:
        if lang == "hi":
            answer_text = "मैंने आपकी सहेजी गई लोकेशन का उपयोग किया है। " + answer_text
        else:
            answer_text = "I'll use your saved location information. " + answer_text
    
    # Create Next Question UI Card
    options = []
    if next_question == "Is this a new business or an existing business?":
        options = ["New Business", "Existing Business"]
        
    ui_cards = []
    if options:
        ui_cards.append(AssistantUICard(
            type=AssistantUICardType.NEXT_QUESTION_CARD,
            question=answer_text,
            options=options
        ))

    # Derive expectedField for the frontend so it can choose the right input mode
    FIELD_MAP = {
        "PIN Code": "pinCode", # Redirects user to profile
        "Is this a new business or an existing business?": "existingBusiness",
        "Estimated Project Cost": "estimatedProjectCost",
        "Course Fee": "estimatedProjectCost",
    }
    expected_field = FIELD_MAP.get(next_question, "general")
        
    return ChatResponse(
        answer=answer_text,
        language=request.language or "en",
        citations=[],
        ui_cards=ui_cards,
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM,
        expected_field=expected_field
    )


# ---------------------------------------------------------------------------
# Deterministic answer normalizer — no LLM needed for button selections
# ---------------------------------------------------------------------------

# YES/NO equivalents across all supported languages + common typos
_YES_ANSWERS = {
    "yes", "हाँ", "हां", "ha", "हा", "हो", "ji", "ji ha", "ji haan",
    "হ্যাঁ", "হা", "ஆம்", "ஆமாம்", "అవును", "हो",
    "y", "true", "1",
}
_NO_ANSWERS = {
    "no", "नहीं", "नही", "na", "नाही", "না", "இல்லை", "కాదు",
    "n", "false", "0",
}

# "New Business" button label equivalents
_NEW_BUSINESS_ANSWERS = {
    "new business", "नया व्यवसाय", "नवीन व्यवसाय", "নতুন ব্যবসা",
    "புதிய தொழில்", "కొత్త వ్యాపారం", "new", "नया",
}

# "Existing Business" button label equivalents
_EXISTING_BUSINESS_ANSWERS = {
    "existing business", "मौजूदा व्यवसाय", "विद्यमान व्यवसाय", "বিদ্যমান ব্যবসা",
    "ஏற்கனவே உள்ள தொழில்", "ఉన్న వ్యాపారం", "existing", "मौजूदा",
}

def normalize_indic_digits(text: str) -> str:
    devanagari = "०१२३४५६७८९"
    for i, d in enumerate(devanagari):
        text = text.replace(d, str(i))
    return text

_PIN_PATTERN = __import__("re").compile(r"(?<!\d)([1-9]\d{5})(?!\d)")
_COST_PATTERN = __import__("re").compile(
    r"(?:₹\s*)?(\d[\d,]*(?:\.\d+)?)\s*(?:lakh|lac|लाख|हजार|thousand|k)?", __import__("re").IGNORECASE
)


def _try_deterministic_parse(query: str, profile: ChatProfile) -> dict:
    """
    Attempt to extract profile fields from a query WITHOUT calling the LLM.
    Returns a dict of {field_name: value} for any fields it could determine.
    Returns an empty dict if the query is ambiguous and needs LLM processing.
    """
    q = query.strip().lower()
    query_norm = normalize_indic_digits(q)
    updates: dict = {}

    # Check New/Existing business answer
    if profile.existingBusiness is None:
        # Add extra mappings from user request
        new_biz = _NEW_BUSINESS_ANSWERS | {"नया व्यवसाय", "नया बिजनेस", "नई शुरुआत", "शुरू करना है", "पहले से नहीं है"}
        old_biz = _EXISTING_BUSINESS_ANSWERS | {"पुराना व्यवसाय", "मौजूदा व्यवसाय", "पहले से व्यवसाय", "पहले से चल रहा है", "पहले से है"}
        
        if any(term in q for term in new_biz):
            updates["existingBusiness"] = False
            return updates
        if any(term in q for term in old_biz):
            updates["existingBusiness"] = True
            return updates

    # Explicit PIN change intent check
    change_pin_phrases = ["change", "update", "new pin", "instead", "बदलना", "नया पिन", "दूसरा", "बदलकर"]
    is_explicit_change = any(p in q for p in change_pin_phrases)

    # Check for PIN code (6-digit number starting with 1-9)
    # Be careful not to match large loan amounts like 500000 as a PIN code.
    # If the bot was asking for a PIN code, missing_fields would be asking for it.
    # To be safe, if we see a 6-digit number, we should check if it's explicitly a PIN change,
    # or if we are actively looking for a PIN code (pinCode is None AND no other large numbers expected).
    if profile.pinCode is None or is_explicit_change:
        pins = _PIN_PATTERN.findall(query_norm)
        if pins:
            # If it's a multiple of 50000 (like 500000, 150000), it's very likely an amount, not a PIN.
            # Real PIN codes like 110001, 560001 are rarely perfectly round numbers.
            # But let's just make sure it's not a round number.
            pin_val = int(pins[0])
            if pin_val % 10000 != 0 or is_explicit_change:
                updates["pinCode"] = pins[0]
                return updates

    # ── Word-to-number resolver for Hindi/Roman Hindi amounts ──────────────
    # "दो लाख" → 200000, "do lakh" → 200000, "teen lakh" → 300000, etc.
    _WORD_NUMS = {
        # Hindi Devanagari
        "एक": 1, "दो": 2, "तीन": 3, "चार": 4, "पाँच": 5, "पांच": 5,
        "छह": 6, "छः": 6, "सात": 7, "आठ": 8, "नौ": 9, "दस": 10,
        "बीस": 20, "पचास": 50, "सौ": 100,
        # Roman Hindi
        "ek": 1, "do": 2, "teen": 3, "char": 4, "panch": 5,
        "chhe": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "bis": 20, "pachas": 50, "sau": 100,
        # English
        "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "twenty": 20, "fifty": 50, "hundred": 100,
    }
    def _resolve_word_amount(text: str) -> int | None:
        import re as _re
        for word, num in _WORD_NUMS.items():
            # Match "<word> lakh/लाख"
            if _re.search(rf"\b{_re.escape(word)}\s+(?:lakh|lac|लाख)\b", text, _re.IGNORECASE):
                return int(num * 100_000)
            # Match "<word> thousand/हजार/k"
            if _re.search(rf"\b{_re.escape(word)}\s+(?:thousand|हजार|k)\b", text, _re.IGNORECASE):
                return int(num * 1_000)
        return None

    # ── Education level / course detection ─────────────────────────────────
    # If profile has no activity or is still vague, and user answers with a course name,
    # map it directly without the LLM.
    _EDU_LEVEL_MAP = {
        "5th": "CLASS_5", "5वीं": "CLASS_5",
        "8th": "CLASS_8", "8वीं": "CLASS_8",
        "10th": "CLASS_10", "10वीं": "CLASS_10", "दसवीं": "CLASS_10", "matric": "CLASS_10",
        "12th": "CLASS_12", "12वीं": "CLASS_12", "बारहवीं": "CLASS_12",
        "intermediate": "CLASS_12", "higher secondary": "CLASS_12",
        "iti": "ITI_DIPLOMA", "polytechnic": "DIPLOMA",
        "btech": "BTECH", "b.tech": "BTECH", "b tech": "BTECH", "बीटेक": "BTECH",
        "be": "BE", "b.e.": "BE",
        "bca": "BCA", "mca": "MCA", "mtech": "MTECH", "m.tech": "MTECH",
        "mbbs": "MBBS", "bds": "BDS", "bams": "BAMS", "bhms": "BHMS",
        "medical": "MEDICAL_GENERAL", "मेडिकल": "MEDICAL_GENERAL",
        "nursing": "NURSING", "नर्सिंग": "NURSING", "gnm": "NURSING", "anm": "NURSING",
        "pharmacy": "PHARMACY", "b.pharm": "PHARMACY", "फार्मेसी": "PHARMACY",
        "mba": "MBA", "bba": "BBA",
        "bsc": "BSC", "msc": "MSC", "bcom": "BCOM", "mcom": "MCOM",
        "ba": "BA", "ma": "MA",
        "llb": "LLB", "law": "LLB",
        "diploma": "DIPLOMA", "graduation": "GRADUATION",
        "engineering": "ENGINEERING_GENERAL", "इंजीनियरिंग": "ENGINEERING_GENERAL",
    }
    if profile.projectType == "EDUCATION":
        matched_edu = None
        q_lower_edu = q.strip()
        for keyword, edu_val in _EDU_LEVEL_MAP.items():
            if keyword in q_lower_edu:
                matched_edu = edu_val
                break
        if matched_edu:
            updates["activity"] = matched_edu
            return updates

    # Check for a numeric project cost or requested amount
    if profile.estimatedProjectCost is None or True: # We should always try to parse amount if the user says it
        # Try word-number resolution first (e.g. "दो लाख", "do lakh")
        word_amount = _resolve_word_amount(query_norm)
        if word_amount:
            updates["estimatedProjectCost"] = word_amount
            return updates

        # Strip common prefix words and try to find a number
        stripped = __import__("re").sub(
            r"(?:project cost|cost|estimate|budget|amount|approximately|around|about|लागत|खर्च|budget)\s*[:=]?\s*",
            "",
            query_norm,
            flags=__import__("re").IGNORECASE,
        )
        
        # Additional parsing for plain numbers (like "500000") which might not be caught if user just says the number
        bare_number_match = __import__("re").search(r"^\s*(\d[\d,]*)\s*$", query_norm)
        if bare_number_match:
            raw = bare_number_match.group(1).replace(",", "")
            try:
                amount = int(raw)
                if amount >= 1000: # Ensure it's a realistic loan amount
                    updates["estimatedProjectCost"] = amount
                    return updates
            except ValueError:
                pass

        # Match numbers with optional lakh/thousand suffixes
        for m in _COST_PATTERN.finditer(stripped):
            raw = m.group(1).replace(",", "")
            try:
                amount = float(raw)
                suffix_text = m.group(0).lower()
                if "lakh" in suffix_text or "lac" in suffix_text or "लाख" in suffix_text:
                    amount *= 100_000
                elif "thousand" in suffix_text or "हजार" in suffix_text or suffix_text.endswith("k"):
                    amount *= 1_000
                updates["estimatedProjectCost"] = int(amount)
                return updates
            except ValueError:
                pass

    return updates


def _extract_profile_data_from_query(query: str, profile: ChatProfile, session_id: str, user_id: str = None):
    # 1. Try deterministic parsing first (no LLM call, no latency)
    deterministic = _try_deterministic_parse(query, profile)
    
    def _sync_persistent_fields(updates: dict):
        if not user_id:
            return
        if "pinCode" in updates or "fullName" in updates:
            from app.services.storage import get_profile_store
            store = get_profile_store()
            persistent = store.get(user_id) or {}
            
            if "pinCode" in updates:
                if "address" not in persistent:
                    persistent["address"] = {}
                persistent["address"]["pinCode"] = updates["pinCode"]
                print(f"[PROFILE] Saving PIN: {updates['pinCode']}")
                
            if "fullName" in updates:
                persistent["fullName"] = updates["fullName"]
                print(f"[PROFILE] Saving Name: {updates['fullName']}")
                
            store.upsert(user_id, persistent)
            print(f"[PROFILE] Profile saved successfully for user: {user_id}")

    if deterministic:
        for k, v in deterministic.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        update_session_profile(session_id, profile)
        _sync_persistent_fields(deterministic)
        print(f"[Guided] Deterministic parse: {deterministic}")
        return


    # 2. Fall back to LLM for ambiguous inputs (e.g. freeform city/state names)
    from app.rag.memory import get_recent_turns
    history = get_recent_turns(session_id)
    history_text = "\n".join([f"Assistant: {t['answer']}\nUser: {t['query']}" for t in history[-3:]]) if history else ""

    system_prompt = f"""Extract profile information from the user's query.
Current known profile: {profile.model_dump_json(exclude_none=True)}
Recent Conversation History:
{history_text}

Update fields if the user provided them.
Available fields: fullName (string), stateCode (string), districtCode (string), pinCode (string), existingBusiness (bool), estimatedProjectCost (int), annualFamilyIncome (int), activity (string).
Return a JSON object with ONLY the updated fields. Do NOT invent information.
Return ONLY raw JSON text. DO NOT wrap it in markdown blocks.
"""
    try:
        model = _llm_model()
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0.1
        )

        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        print(f"[Guided] LLM extracted profile data: {data}")

        for k, v in data.items():
            if hasattr(profile, k):
                setattr(profile, k, v)

        update_session_profile(session_id, profile)
        _sync_persistent_fields(data)
    except Exception as e:
        print(f"[Guided] Error extracting profile via LLM: {e}")


def _handle_scheme_recommendation(request: ChatRequest, profile: ChatProfile, session_id: str, is_transition: bool = False) -> ChatResponse:
    purpose = profile.activity or "BUSINESS"
    is_edu = profile.projectType == "EDUCATION"
    
    # 1. Map to Eligibility Engine format
    user_profile = {
        "purpose": purpose,
        "family_income_inr": profile.annualFamilyIncome or 0,
        "project_cost_inr": 0 if is_edu else (profile.estimatedProjectCost or 0),
        "course_cost_inr": (profile.estimatedProjectCost or 0) if is_edu else 0,
        "beneficiary_category_verified": True,
        "education_status": "admission_secured" if is_edu else None
    }
    
    # 2. Run deterministic engines
    eval_response = evaluate_all_schemes(user_profile)
    ranked = generate_recommendations(eval_response)
    
    top = ranked.top_recommendation
    lang = (request.language or "").strip().lower() or "en"
    
    if not top:
        profile.conversationState = ConversationState.PARTNER_SEARCH
        update_session_profile(session_id, profile)
        
        no_scheme_map = {
            "en": "Based on the information provided, I could not confirm a matching verified scheme yet. Let me help you find a channel partner who can assist you further.",
            "hi": "दी गई जानकारी के आधार पर, मुझे अभी तक कोई मेल खाने वाली सत्यापित योजना नहीं मिली है। मैं आपको एक चैनल पार्टनर खोजने में मदद करता हूँ जो आपकी आगे की सहायता कर सके।",
            "mr": "दिलेल्या माहितीच्या आधारे, मला अद्याप कोणतीही जुळणारी सत्यापित योजना सापडली नाही. मी तुम्हाला एक चॅनेल भागीदार शोधण्यात मदत करतो जो तुम्हाला पुढील मदत करू शकेल.",
            "bn": "প্রদত্ত তথ্যের উপর ভিত্তি করে, আমি এখনও কোনও যাচাইকৃত স্কিম নিশ্চিত করতে পারিনি। আমি আপনাকে একজন চ্যানেল পার্টনার খুঁজে পেতে সাহায্য করছি যিনি আপনাকে আরও সহায়তা করতে পারবেন।",
            "ta": "வழங்கப்பட்ட தகவலின் அடிப்படையில், பொருத்தமான சரிபார்க்கப்பட்ட திட்டத்தை என்னால் இன்னும் உறுதிப்படுத்த முடியவில்லை. உங்களுக்கு மேலும் உதவக்கூடிய சேனல் பார்ட்னரைக் கண்டறிய நான் உதவுகிறேன்.",
            "te": "అందించిన సమాచారం ఆధారంగా, నేను ఇంకా సరిపోలే ధృవీకరించబడిన పథకాన్ని నిర్ధారించలేకపోయాను. మీకు మరింత సహాయం చేయగల ఛానెల్ భాగస్వామిని కనుగొనడంలో నేను మీకు సహాయం చేస్తాను."
        }
        answer_text = no_scheme_map.get(lang, no_scheme_map["en"])
        
        return ChatResponse(
            answer=answer_text,
            language=lang,
            citations=[],
            ui_cards=[AssistantUICard(type=AssistantUICardType.WARNING_CARD, message="No eligible scheme found.")],
            grounding_status="GROUNDED",
            response_source=ResponseSource.RAG_LLM
        )
        
    # Look up the scheme from the loader
    from app.api.scheme_loader import get_scheme_by_internal_id
    scheme_api = get_scheme_by_internal_id(top.scheme_id)
    requires_partner = scheme_api.get("channelPartnerRequired", False) if scheme_api else False
    
    # Store in profile
    profile.recommendedSchemeId = top.scheme_id
    profile.channelPartnerRequired = requires_partner
    
    reason_map = {
        "en": "You meet the eligibility criteria for this scheme.",
        "hi": "आप इस योजना के पात्रता मानदंडों को पूरा करते हैं।",
        "mr": "तुम्ही या योजनेच्या पात्रतेचे निकष पूर्ण करता.",
        "bn": "আপনি এই প্রকল্পের যোগ্যতার মানদণ্ড পূরণ করেছেন।",
        "ta": "நீங்கள் இந்த திட்டத்திற்கான தகுதி அளவுகோல்களை பூர்த்தி செய்கிறீர்கள்.",
        "te": "మీరు ఈ పథకానికి అర్హత ప్రమాణాలను పూర్తి చేస్తున్నారు."
    }
    reason_text = reason_map.get(lang, reason_map["en"])
    
    # 3. Generate Scheme Recommendation Card
    ui_cards = [
        AssistantUICard(
            type=AssistantUICardType.SCHEME_CARD,
            schemeId=scheme_api.get("id") if scheme_api else top.scheme_id,
            schemeName=top.scheme_name,
            reason=reason_text,
            eligible=True
        ),
        AssistantUICard(
            type=AssistantUICardType.NEXT_QUESTION_CARD,
            question="What would you like to do next?" if lang == "en" else "आप आगे क्या करना चाहेंगे?",
            options=["Find Channel Partners", "View Required Documents"] if lang == "en" else ["चैनल पार्टनर खोजें", "आवश्यक दस्तावेज़ देखें"]
        )
    ]
    
    # 4. Retrieve context for the recommended scheme
    from app.rag.retriever import retrieve_scheme_context
    retrieved_chunks = retrieve_scheme_context(top.scheme_id, max_chunks=3)
    context_text = "\n\n".join([rc.chunk.text for rc in retrieved_chunks])
    
    # 5. Generate LLM Explanation
    lang_names = {"hi": "Hindi", "en": "English", "mr": "Marathi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu"}
    lang_name = lang_names.get(request.language, "English")
    system_prompt = f"""You are SAARTHI, an NSFDC assistance assistant.
Based on the user's profile and query context, the deterministic engine recommended the scheme: {top.scheme_name}.

User profile summary:
Purpose/Activity: {purpose}
Project Cost / Course Fee: {profile.estimatedProjectCost}
Family Income: {profile.annualFamilyIncome}
Location/PIN: {profile.pinCode}

Here is the verified context for this scheme:
{context_text}

Generate a compact, villager-friendly response in {lang_name} following this EXACT structure:

━━━━━━━━━━━━━━━━
आपके लिए उपयुक्त योजना (Translate header to {lang_name})
━━━━━━━━━━━━━━━━

{top.scheme_name}

क्यों? / Why this scheme? (Translate to {lang_name})
• [Point 1: e.g. You mentioned you want to do {purpose}]
• [Point 2: e.g. This scheme supports the relevant income-generating activity]
• [Point 3: e.g. Your project cost/needs match the scheme criteria]

योजना की जानकारी / Scheme Details: (Translate to {lang_name})
• Loan / वित्तीय सहायता: [Extract from context]
• Interest / ब्याज: [Extract from context]
• Repayment / भुगतान अवधि: [Extract from context]
• Eligibility / पात्रता: [Extract from context]

आप क्या करना चाहते हैं? / What would you like to do next? (Translate to {lang_name})
• Check EMI
• Find Channel Partners
• View Documents
• Application Process

RULES:
- Do NOT invent loan amounts, interest rates, or eligibility. If not found in the verified context, explicitly say: "इस योजना के उपलब्ध दस्तावेज़ में यह जानकारी नहीं मिली है।" (or equivalent in {lang_name}).
- Do NOT expose internal database fields.
- Keep it simple and easy to read.
- Response MUST be entirely in {lang_name}.
"""
    try:
        model = _llm_model()
        response = litellm.completion(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Please give me the scheme recommendation."}
            ],
            temperature=0.1
        )
        answer_text = response.choices[0].message.content or "Here is the recommended scheme."
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"LLM scheme recommendation generation failed: {e}")
        fallback_map = {
            "en": f"Based on your profile, the recommended scheme is {top.scheme_name}. For full details, please check the scheme document.",
            "hi": f"आपकी प्रोफ़ाइल के आधार पर, {top.scheme_name} आपके लिए सबसे उपयुक्त योजना है। पूरी जानकारी के लिए कृपया योजना दस्तावेज़ देखें।",
            "mr": f"तुमच्या प्रोफाईलच्या आधारे, {top.scheme_name} ही तुमच्यासाठी सर्वात योग्य योजना आहे.",
            "bn": f"আপনার প্রোফাইলের উপর ভিত্তি করে, {top.scheme_name} আপনার জন্য সবচেয়ে উপযুক্ত স্কিম।",
            "ta": f"உங்கள் சுயவிவரத்தின் அடிப்படையில், {top.scheme_name} உங்களுக்கு மிகவும் பொருத்தமான திட்டம்.",
            "te": f"మీ ప్రొఫైల్ ఆధారంగా, {top.scheme_name} మీకు అత్యంత అనుకూలమైన పథకం.",
        }
        answer_text = fallback_map.get(lang_name, fallback_map["en"])

    
    # Transition State
    profile.conversationState = ConversationState.DOCUMENT_PREPARATION
    update_session_profile(session_id, profile)
    
    return ChatResponse(
        answer=answer_text,
        language=request.language or "en",
        citations=[],
        ui_cards=ui_cards,
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM
    )

def _handle_document_preparation(request: ChatRequest, profile: ChatProfile, session_id: str) -> ChatResponse:
    lang = (request.language or "").strip().lower() or "en"
    
    # Base requirements mapping
    docs_map = {
        "en": {
            "req_scheme": ["Caste Certificate", "Identity Proof (Aadhaar)", "Income Certificate"],
            "req_partner": ["Bank Statement", "Passport Size Photographs"],
            "recommended": "Detailed Project Report for ",
            "vault": " ✅ (Already in Vault)",
            "partner_msg": "Here is your document checklist. I have checked your Document Vault and marked the ones you have already uploaded. Would you like me to find a verified Channel Partner near you to help with your application?",
            "direct_msg": "Here is your document checklist. This scheme does not require a channel partner. You can apply directly through the official portal."
        },
        "hi": {
            "req_scheme": ["जाति प्रमाण पत्र", "पहचान प्रमाण (आधार)", "आय प्रमाण पत्र"],
            "req_partner": ["बैंक स्टेटमेंट", "पासपोर्ट साइज फोटो"],
            "recommended": "विस्तृत प्रोजेक्ट रिपोर्ट - ",
            "vault": " ✅ (पहले से वॉल्ट में है)",
            "partner_msg": "यह आपकी दस्तावेज़ सूची है। मैंने आपके वॉल्ट की जाँच की है और जो दस्तावेज़ पहले से अपलोड हैं उन्हें चिह्नित किया है। क्या आप चाहेंगे कि मैं आपके आवेदन के लिए आपके पास एक सत्यापित चैनल पार्टनर खोजूँ?",
            "direct_msg": "यह आपकी दस्तावेज़ सूची है। इस योजना के लिए चैनल पार्टनर की आवश्यकता नहीं है। आप सीधे आधिकारिक पोर्टल के माध्यम से आवेदन कर सकते हैं।"
        },
        "mr": {
            "req_scheme": ["जात प्रमाणपत्र", "ओळखपत्र (आधार)", "उत्पन्न प्रमाणपत्र"],
            "req_partner": ["बँक स्टेटमेंट", "पासपोर्ट साईझ फोटो"],
            "recommended": "सविस्तर प्रकल्प अहवाल - ",
            "vault": " ✅ (आधीच व्हॉल्टमध्ये आहे)",
            "partner_msg": "ही तुमची कागदपत्रांची यादी आहे. मी तुमच्या व्हॉल्टची तपासणी केली आहे आणि जी कागदपत्रे आधीच अपलोड केली आहेत ती चिन्हांकित केली आहेत. तुम्हाला अर्जासाठी जवळपासचा एखादा सत्यापित चॅनेल भागीदार शोधायला आवडेल का?",
            "direct_msg": "ही तुमची कागदपत्रांची यादी आहे. या योजनेसाठी चॅनेल भागीदाराची आवश्यकता नाही. तुम्ही अधिकृत पोर्टलद्वारे थेट अर्ज करू शकता."
        },
        "bn": {
            "req_scheme": ["জাতিগত শংসাপত্র", "পরিচয়পত্র (আধার)", "আয়ের শংসাপত্র"],
            "req_partner": ["ব্যাঙ্ক স্টেটমেন্ট", "পাসপোর্ট সাইজ ছবি"],
            "recommended": "বিস্তারিত প্রকল্প প্রতিবেদন - ",
            "vault": " ✅ (ইতিমধ্যেই ভল্টে আছে)",
            "partner_msg": "এখানে আপনার নথির তালিকা রয়েছে। আমি আপনার ভল্ট চেক করেছি এবং আপনি যেগুলি ইতিমধ্যে আপলোড করেছেন তা চিহ্নিত করেছি। আপনি কি চান যে আমি আপনার আবেদনের জন্য কাছাকাছি একটি যাচাইকৃত চ্যানেল পার্টনার খুঁজি?",
            "direct_msg": "এখানে আপনার নথির তালিকা রয়েছে। এই স্কিমের জন্য চ্যানেল পার্টনারের প্রয়োজন নেই। আপনি সরাসরি অফিসিয়াল পোর্টালে আবেদন করতে পারেন।"
        },
        "ta": {
            "req_scheme": ["சாதி சான்றிதழ்", "அடையாள சான்று (ஆதார்)", "வருமான சான்றிதழ்"],
            "req_partner": ["வங்கி கணக்கு அறிக்கை", "பாஸ்போர்ட் அளவு புகைப்படங்கள்"],
            "recommended": "விரிவான திட்ட அறிக்கை - ",
            "vault": " ✅ (ஏற்கனவே வால்ட்டில் உள்ளது)",
            "partner_msg": "இது உங்கள் ஆவண பட்டியல். நான் உங்கள் வால்ட்டைச் சரிபார்த்து, நீங்கள் ஏற்கனவே பதிவேற்றியவற்றைக் குறித்துள்ளேன். உங்கள் விண்ணப்பத்திற்கு உதவ, அருகிலுள்ள சரிபார்க்கப்பட்ட சேனல் பார்ட்னரைக் கண்டறிய நான் உதவ வேண்டுமா?",
            "direct_msg": "இது உங்கள் ஆவண பட்டியல். இந்த திட்டத்திற்கு சேனல் பார்ட்னர் தேவையில்லை. அதிகாரப்பூர்வ போர்டல் மூலம் நீங்கள் நேரடியாக விண்ணப்பிக்கலாம்."
        },
        "te": {
            "req_scheme": ["కుల ధృవీకరణ పత్రం", "గుర్తింపు రుజువు (ఆధార్)", "ఆదాయ ధృవీకరణ పత్రం"],
            "req_partner": ["బ్యాంక్ స్టేట్‌మెంట్", "పాస్‌పోర్ట్ సైజు ఫోటోలు"],
            "recommended": "వివరణాత్మక ప్రాజెక్ట్ నివేదిక - ",
            "vault": " ✅ (ఇప్పటికే వాల్ట్‌లో ఉంది)",
            "partner_msg": "ఇది మీ పత్రాల జాబితా. నేను మీ వాల్ట్‌ని తనిఖీ చేసి, మీరు ఇప్పటికే అప్‌లోడ్ చేసిన వాటిని గుర్తించాను. మీ దరఖాస్తు కోసం సమీపంలో ఉన్న ధృవీకరించబడిన ఛానెల్ భాగస్వామిని కనుగొనడంలో నేను సహాయం చేయాలా?",
            "direct_msg": "ఇది మీ పత్రాల జాబితా. ఈ పథకానికి ఛానెల్ భాగస్వామి అవసరం లేదు. మీరు అధికారిక పోర్టల్ ద్వారా నేరుగా దరఖాస్తు చేసుకోవచ్చు."
        }
    }
    
    t = docs_map.get(lang, docs_map["en"])
    
    req_by_scheme = t["req_scheme"]
    req_by_partner = t["req_partner"]
    biz_name = profile.activity or ("Business" if lang == "en" else "व्यवसाय")
    recommended = [t["recommended"] + biz_name]
    
    # 2. Check uploaded documents if user_id is provided
    uploaded_categories = set()
    if request.user_id:
        try:
            from app.services.storage import get_document_storage
            docs = get_document_storage().list(request.user_id)
            for d in docs:
                if d.category:
                    uploaded_categories.add(d.category)
        except Exception as e:
            print(f"[Guided] Error reading user vault: {e}")

    # Helper to mark uploaded items
    def _mark_uploaded(items, category_map):
        marked = []
        for item in items:
            cat = category_map.get(item)
            if cat and cat in uploaded_categories:
                marked.append(f"{item}{t['vault']}")
            else:
                marked.append(item)
        return marked

    # Map text labels to DocumentCategory values (across all languages)
    category_map = {
        # CASTE
        "Caste Certificate": "CASTE_CERTIFICATE", "जाति प्रमाण पत्र": "CASTE_CERTIFICATE", 
        "जात प्रमाणपत्र": "CASTE_CERTIFICATE", "জাতিগত শংসাপত্র": "CASTE_CERTIFICATE", 
        "சாதி சான்றிதழ்": "CASTE_CERTIFICATE", "కుల ధృవీకరణ పత్రం": "CASTE_CERTIFICATE",
        # IDENTITY
        "Identity Proof (Aadhaar)": "IDENTITY_PROOF", "पहचान प्रमाण (आधार)": "IDENTITY_PROOF", 
        "ओळखपत्र (आधार)": "IDENTITY_PROOF", "পরিচয়পত্র (আধার)": "IDENTITY_PROOF", 
        "அடையாள சான்று (ஆதார்)": "IDENTITY_PROOF", "గుర్తింపు రుజువు (ఆధార్)": "IDENTITY_PROOF",
        # INCOME
        "Income Certificate": "INCOME_CERTIFICATE", "आय प्रमाण पत्र": "INCOME_CERTIFICATE", 
        "उत्पन्न प्रमाणपत्र": "INCOME_CERTIFICATE", "আয়ের শংসাপত্র": "INCOME_CERTIFICATE", 
        "வருமான சான்றிதழ்": "INCOME_CERTIFICATE", "ఆదాయ ధృవీకరణ పత్రం": "INCOME_CERTIFICATE",
        # BANK
        "Bank Statement": "BANK_STATEMENT", "बैंक स्टेटमेंट": "BANK_STATEMENT", 
        "बँक स्टेटमेंट": "BANK_STATEMENT", "ব্যাঙ্ক স্টেটমেন্ট": "BANK_STATEMENT", 
        "வங்கி கணக்கு அறிக்கை": "BANK_STATEMENT", "బ్యాంక్ స్టేట్‌మెంట్": "BANK_STATEMENT",
        # PHOTO
        "Passport Size Photographs": "PHOTOGRAPH", "पासपोर्ट साइज फोटो": "PHOTOGRAPH", 
        "पासपोर्ट साईझ फोटो": "PHOTOGRAPH", "পাসপোর্ট সাইজ ছবি": "PHOTOGRAPH", 
        "பாஸ்போர்ட் அளவு புகைப்படங்கள்": "PHOTOGRAPH", "పాస్‌పోర్ట్ సైజు ఫోటోలు": "PHOTOGRAPH",
        # BUSINESS PLAN
        recommended[0]: "BUSINESS_PLAN"
    }

    # Build a checklist with marks
    checklist_card = AssistantUICard(
        type=AssistantUICardType.DOCUMENT_CHECKLIST,
        requiredByScheme=_mark_uploaded(req_by_scheme, category_map),
        requiredByPartner=_mark_uploaded(req_by_partner, category_map),
        recommended=_mark_uploaded(recommended, category_map)
    )
    
    if profile.channelPartnerRequired:
        answer_text = t["partner_msg"]
        profile.conversationState = ConversationState.PARTNER_SEARCH
    else:
        answer_text = t["direct_msg"]
        profile.conversationState = ConversationState.APPLICATION_GUIDANCE
    
    update_session_profile(session_id, profile)
    
    return ChatResponse(
        answer=answer_text,
        language=request.language or "en",
        citations=[],
        ui_cards=[checklist_card],
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM
    )

def _handle_partner_search(request: ChatRequest, profile: ChatProfile, session_id: str, is_transition: bool = False) -> ChatResponse:
    if not is_transition:
        _extract_profile_data_from_query(request.query, profile, session_id, request.user_id)
        profile = get_session_profile(session_id)
        
    lang = (request.language or "").strip().lower() or "en"
    
    # Missing PIN Code maps
    pin_map = {
        "en": "I need your 6-digit PIN code to find a channel partner near you. Please update it in your Profile first.",
        "hi": "मुझे आपके आस-पास एक चैनल पार्टनर खोजने के लिए आपका 6 अंकों का पिन कोड चाहिए। कृपया पहले इसे अपने प्रोफाइल में अपडेट करें।",
        "mr": "मला तुमच्या जवळपास एक चॅनेल भागीदार शोधण्यासाठी तुमचा 6-अंकी पिन कोड आवश्यक आहे. कृपया प्रथम ते तुमच्या प्रोफाइलमध्ये अपडेट करा.",
        "bn": "আপনার কাছাকাছি একটি চ্যানেল পার্টনার খুঁজে পেতে আমার আপনার ৬-সংখ্যার পিন কোড দরকার। অনুগ্রহ করে প্রথমে এটি আপনার প্রোফাইলে আপডেট করুন।",
        "ta": "உங்களுக்கு அருகிலுள்ள ஒரு சேனல் கூட்டாளரைக் கண்டறிய உங்கள் 6 இலக்க பின் குறியீடு எனக்குத் தேவை. தயவுசெய்து முதலில் அதை உங்கள் சுயவிவரத்தில் புதுப்பிக்கவும்.",
        "te": "మీకు సమీపంలోని ఛానెల్ భాగస్వామిని కనుగొనడానికి నాకు మీ 6-అంకెల పిన్ కోడ్ కావాలి. దయచేసి ముందుగా దాన్ని మీ ప్రొఫైల్‌లో అప్‌డేట్ చేయండి."
    }
    
    # Found partner maps
    found_map = {
        "en": "I found a verified channel partner near you. They are located approximately {dist} km away.",
        "hi": "मुझे आपके आस-पास एक सत्यापित चैनल पार्टनर मिला है। वे लगभग {dist} किलोमीटर दूर स्थित हैं।",
        "mr": "मला तुमच्या जवळपास एक सत्यापित चॅनेल भागीदार सापडला आहे. ते सुमारे {dist} किलोमीटर अंतरावर आहेत.",
        "bn": "আমি আপনার কাছাকাছি একটি যাচাইকৃত চ্যানেল পার্টনার খুঁজে পেয়েছি। তারা প্রায় {dist} কিলোমিটার দূরে অবস্থিত।",
        "ta": "உங்களுக்கு அருகில் சரிபார்க்கப்பட்ட சேனல் பார்ட்னரை நான் கண்டறிந்தேன். அவர்கள் சுமார் {dist} கி.மீ தொலைவில் உள்ளனர்.",
        "te": "నేను మీ సమీపంలో ఒక ధృవీకరించబడిన ఛానెల్ భాగస్వామిని కనుగొన్నాను. వారు సుమారు {dist} కి.మీ దూరంలో ఉన్నారు."
    }
    
    # Not found maps
    not_found_map = {
        "en": "I could not find a verified channel partner near your location.",
        "hi": "मुझे आपके स्थान के पास कोई सत्यापित चैनल पार्टनर नहीं मिला।",
        "mr": "मला तुमच्या ठिकाणाजवळ कोणताही सत्यापित चॅनेल भागीदार सापडला नाही.",
        "bn": "আমি আপনার অবস্থানের কাছাকাছি কোনও যাচাইকৃত চ্যানেল পার্টনার খুঁজে পাইনি।",
        "ta": "உங்கள் இருப்பிடத்திற்கு அருகில் சரிபார்க்கப்பட்ட சேனல் பார்ட்னரை என்னால் கண்டறிய முடியவில்லை.",
        "te": "మీ స్థానానికి సమీపంలో నాకు ధృవీకరించబడిన ఛానెల్ భాగస్వామి ఎవరూ దొరకలేదు."
    }
    
    if not profile.pinCode:
        answer_text = pin_map.get(lang, pin_map["en"])
        return ChatResponse(
            answer=answer_text,
            language=lang,
            citations=[],
            ui_cards=[],
            grounding_status="GROUNDED",
            response_source=ResponseSource.RAG_LLM
        )
        
    from app.rag.partner_repo import get_partner_repo
    repo = get_partner_repo()
    
    partners = repo.search_by_pincode_with_expansion(
        pincode=profile.pinCode,
        scheme_id=profile.recommendedSchemeId,
        lat=profile.latitude,
        lon=profile.longitude
    )
    
    ui_cards = []
    if partners:
        p = partners[0]
        ui_cards.append(AssistantUICard(
            type=AssistantUICardType.PARTNER_CARD,
            partnerId=p.get("partnerId"),
            name=p.get("name", ""),
            distanceKm=p.get("distance_km"),
            address=p.get("address", "")
        ))
        answer_text = found_map.get(lang, found_map["en"]).format(dist=p.get("distance_km"))
    else:
        answer_text = not_found_map.get(lang, not_found_map["en"])
        ui_cards.append(AssistantUICard(
            type=AssistantUICardType.PARTNER_CARD
        ))
    
    profile.conversationState = ConversationState.COMPLETED
    update_session_profile(session_id, profile)
    
    return ChatResponse(
        answer=answer_text,
        language=request.language or "en",
        citations=[],
        ui_cards=ui_cards,
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM
    )
