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
    loan_keywords = ["loan", "लोन", "ऋण", "कर्ज", "finance", "financing"]
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
        "SHOP": ["shop", "dukan", "दुकान", "store"]
    }
    
    for activity, aliases in ACTIVITY_ALIASES.items():
        if any(alias in query_lower for alias in aliases):
            return {"intent": "LOAN", "activity": activity}
            
    return {"intent": "LOAN", "activity": "GENERAL_BUSINESS"}

def _handle_initial_query(request: ChatRequest, profile: ChatProfile, session_id: str) -> ChatResponse:
    # Deterministic check first
    data = _deterministic_intent_extraction(request.query)
    if data and data.get("intent") == "LOAN":
        print(f"Deterministic intent extracted: {data}")
        profile.activity = data.get("activity")
        profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
        update_session_profile(session_id, profile)
        return _handle_collecting_eligibility(request, profile, session_id, is_transition=True)
    
    system_prompt = f"""You are SAARTHI, a scheme advisory assistant.
Determine if the user's query is explicitly asking for a LOAN or FINANCIAL CREDIT for a specific business, education, or activity (e.g., dairy farming, poultry, new business, education loan).
If the user is asking for a scholarship, grant, skill training, or general support, it is NOT a loan.
If yes (it is a loan), you MUST return exactly this JSON object:
{{"intent": "LOAN", "activity": "<ACTIVITY>"}}
If no, return exactly this JSON object:
{{"intent": "GENERAL"}}
Do not include any other text.
"""
    model = _llm_model()
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request.query}
        ],
        temperature=0.1
    )
    
    try:
        content = (response.choices[0].message.content or "").strip()
        if content.startswith("```json"):
            content = content.replace("```json", "").replace("```", "").strip()
        data = json.loads(content)
        print(f"Extracted intent data: {data}")
        
        if data.get("intent") == "LOAN":
            # Update profile and state
            profile.activity = data.get("activity")
            profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
            update_session_profile(session_id, profile)
            
            # Now trigger the collecting eligibility step to ask the first question
            return _handle_collecting_eligibility(request, profile, session_id, is_transition=True)
    except Exception as e:
        print(f"Error parsing initial query intent: {e}")
        pass
        
    # If not a loan intent, use standard RAG (we can route back to standard chat)
    return None

def _handle_collecting_eligibility(request: ChatRequest, profile: ChatProfile, session_id: str, is_transition: bool = False) -> ChatResponse:
    # If this is not a direct transition, we need to extract the user's answer from their query
    if not is_transition:
        _extract_profile_data_from_query(request.query, profile, session_id, request.user_id)
        # Update session profile with extracted data before checking missing fields
        update_session_profile(session_id, profile)
        
    # Check what is missing
    missing_fields = []
    if profile.pinCode is None and (profile.stateCode is None or profile.districtCode is None):
        missing_fields.append("State and District or PIN Code")
    elif profile.existingBusiness is None:
        missing_fields.append("Is this a new business or an existing business?")
    elif profile.estimatedProjectCost is None:
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
            "State and District or PIN Code": "Please enter your PIN code.",
            "Is this a new business or an existing business?": "Is this a new business or an existing business?",
            "Estimated Project Cost": "What is the estimated total project cost?"
        },
        "hi": {
            "State and District or PIN Code": "कृपया अपना 6 अंकों का पिन कोड बताएं।",
            "Is this a new business or an existing business?": "क्या यह नया व्यवसाय है या आपका पहले से चल रहा व्यवसाय है?",
            "Estimated Project Cost": "इस परियोजना की अनुमानित कुल लागत कितनी है?"
        },
        "mr": {
            "State and District or PIN Code": "कृपया तुमचे राज्य, जिल्हा किंवा पिन कोड सांगा.",
            "Is this a new business or an existing business?": "हा नवीन व्यवसाय आहे की जुना?",
            "Estimated Project Cost": "अंदाजित प्रकल्प खर्च किती आहे?"
        },
        "bn": {
            "State and District or PIN Code": "দয়া করে আপনার রাজ্য, জেলা বা পিন কোড শেয়ার করুন।",
            "Is this a new business or an existing business?": "এটি কি একটি নতুন ব্যবসা না বিদ্যমান ব্যবসা?",
            "Estimated Project Cost": "আনুমানিক প্রকল্প ব্যয় কত?"
        },
        "ta": {
            "State and District or PIN Code": "உங்கள் மாநிலம், மாவட்டம் அல்லது பின் குறியீட்டைப் பகிரவும்.",
            "Is this a new business or an existing business?": "இது புதிய தொழிலா அல்லது ஏற்கனவே உள்ள தொழிலா?",
            "Estimated Project Cost": "மதிப்பிடப்பட்ட திட்ட செலவு என்ன?"
        },
        "te": {
            "State and District or PIN Code": "దయచేసి మీ రాష్ట్రం, జిల్లా లేదా పిన్ కోడ్‌ను పంచుకోండి.",
            "Is this a new business or an existing business?": "ఇది కొత్త వ్యాపారమా లేదా ఉన్న వ్యాపారమా?",
            "Estimated Project Cost": "అంచనా ప్రాజెక్ట్ వ్యయం ఎంత?"
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
        "State and District or PIN Code": "pinCode",
        "Is this a new business or an existing business?": "existingBusiness",
        "Estimated Project Cost": "estimatedProjectCost",
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
    if profile.pinCode is None or is_explicit_change:
        pins = _PIN_PATTERN.findall(query_norm)
        if pins:
            updates["pinCode"] = pins[0]
            return updates

    # Check for a numeric project cost
    if profile.estimatedProjectCost is None:
        # Strip common prefix words and try to find a number
        stripped = __import__("re").sub(
            r"(?:project cost|cost|estimate|budget|amount|approximately|around|about|लागत|खर्च|budget)\s*[:=]?\s*",
            "",
            query_norm,
            flags=__import__("re").IGNORECASE,
        )
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
Available fields: fullName (string), stateCode (string), districtCode (string), pinCode (string), existingBusiness (bool), estimatedProjectCost (int), annualFamilyIncome (int).
Return a JSON object with ONLY the updated fields. Do NOT invent information.
Return ONLY raw JSON text. DO NOT wrap it in markdown blocks.
"""
    model = _llm_model()
    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": query}
        ],
        temperature=0.1
    )

    try:
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
    # 1. Map to Eligibility Engine format
    user_profile = {
        "purpose": profile.activity or "BUSINESS",
        "family_income_inr": profile.annualFamilyIncome or 0,
        "project_cost_inr": profile.estimatedProjectCost or 0,
        "beneficiary_category_verified": True
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
        )
    ]
    
    # 4. Generate LLM Explanation
    lang_names = {"hi": "Hindi", "en": "English", "mr": "Marathi", "bn": "Bengali", "ta": "Tamil", "te": "Telugu"}
    lang_name = lang_names.get(request.language, "English")
    system_prompt = f"""You are SAARTHI.
Based on the user's profile, the deterministic engine recommended the scheme: {top.scheme_name}.
Explain why this scheme matches their needs (e.g. Project Cost is within limits).
Do NOT invent loan amounts or interest rates if it's not a financial scheme. Use terms like "possible eligibility".
Then, ask the user if they would like to check their required documents next.
RESPONSE LANGUAGE: {lang_name}
You MUST answer entirely in {lang_name}.
"""
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
        "en": "Please provide your 6-digit PIN code so I can find a verified channel partner near you.",
        "hi": "कृपया मुझे अपना 6 अंकों का पिन कोड बताएं ताकि मैं आपके आस-पास एक सत्यापित चैनल पार्टनर खोज सकूं।",
        "mr": "कृपया मला तुमचा 6-अंकी पिन कोड सांगा जेणेकरून मी तुमच्या जवळपास एखादा सत्यापित चॅनेल भागीदार शोधू शकेन.",
        "bn": "অনুগ্রহ করে আপনার ৬-সংখ্যার পিন কোড প্রদান করুন যাতে আমি আপনার কাছাকাছি একটি যাচাইকৃত চ্যানেল পার্টনার খুঁজে পেতে পারি।",
        "ta": "தயவுசெய்து உங்கள் 6-இலக்க பின் குறியீட்டை வழங்கவும், இதன் மூலம் உங்களுக்கு அருகிலுள்ள சரிபார்க்கப்பட்ட சேனல் பார்ட்னரைக் கண்டறிய முடியும்.",
        "te": "దయచేసి మీ 6-అంకెల పిన్ కోడ్‌ను అందించండి, తద్వారా నేను మీ సమీపంలో ధృవీకరించబడిన ఛానెల్ భాగస్వామిని కనుగొనగలను."
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
    
    partners = repo.search_by_pincode_with_expansion(profile.pinCode)
    
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
