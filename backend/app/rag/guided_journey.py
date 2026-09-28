import json
import os
import re
import uuid
from typing import Dict, Any, List, Optional

import litellm

from app.schemas.chat import ChatRequest, ChatResponse, ChatProfile, ConversationState, ResponseSource
from app.schemas.assistant import AssistantUICard, AssistantUICardType
from app.rag.memory import get_history, get_session_profile, update_session_profile, add_turn
from app.eligibility_engine import evaluate_all_schemes, load_scheme
from app.recommendation_engine import generate_recommendations, RelevanceQuery
from types import SimpleNamespace

from app.rag.language_detect import detect_language_and_intent, extract_specific_activity
from app.rag.query_context import build_retrieval_query
from app.rag.scheme_advisor import (
    BUSINESS_CREDIT_IDS,
    COMPARE,
    DISCOVERY,
    EDUCATION_CREDIT_IDS,
    EXPLAIN,
    OPTIONS,
    build_brief,
    detect_adviser_mode,
    ui_cards as adviser_ui_cards,
)
from app.rag.retriever import retrieve, retrieve_ranked_schemes
from app.services.storage import get_profile_store

_INTENT_TO_PROJECT = {
    "EDUCATION_LOAN": "EDUCATION",
    "AGRICULTURE": "AGRICULTURE",
    "BUSINESS": "BUSINESS",
}
_NO_MATCH_MARKERS = (
    "no verified",
    "not invent",
    "will not invent",
    "गढ़ नहीं",
    "पुष्टि नहीं हुई",
    "कोई सत्यापित",
    "could not confirm",
    "no matching verified",
    "कोई योजना गढ़",
)

def _llm_model() -> str:
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL environment variable is not set.")
    return model


def _answer_denies_schemes(text: str) -> bool:
    low = (text or "").lower()
    return any(marker.lower() in low for marker in _NO_MATCH_MARKERS)


def _unique_retrieved_schemes(retrieved_chunks: list) -> list:
    seen: set[str] = set()
    out = []
    for rc in retrieved_chunks or []:
        chunk = getattr(rc, "chunk", None)
        if chunk is None or chunk.scheme_id in seen:
            continue
        seen.add(chunk.scheme_id)
        out.append(chunk)
    return out


def _conversation_amount(profile: ChatProfile) -> Optional[int]:
    if profile.projectType == "EDUCATION":
        return profile.requestedLoanAmount
    return profile.estimatedProjectCost or profile.requestedLoanAmount


_EDU_QUERY_MARKERS = (
    "education", "study", "studies", "student", "college", "school",
    "padhai", "padai", "shiksha", "scholarship", "fellowship", "coaching",
    "btech", "b.tech", "पढ़ाई", "शिक्षा", "स्कॉलरशिप", "छात्रवृत्ति",
)


def _query_suggests_education(query: str) -> bool:
    q = (query or "").lower()
    return any(m in q for m in _EDU_QUERY_MARKERS)


def _education_course(profile: ChatProfile) -> Optional[str]:
    act = profile.activity
    token = str(act or "").upper()
    if token and token not in {"EDUCATION", "EDUCATION_LOAN", "GENERAL"}:
        return act
    return profile.educationStatus or act


def _education_expected_field(missing: list[str], fallback: str | None = "general") -> str:
    if "requested_amount" in missing:
        return "requestedLoanAmount"
    if "course" in missing:
        return "activity"
    if "income" in missing:
        return "annualFamilyIncome"
    return fallback or "general"


def _retrieve_adviser_scheme_ids(request: ChatRequest, profile: ChatProfile, lang: str) -> list[str]:
    """Retrieve NSFDC credit candidates from the merged conversation query."""
    retrieval_spec = build_retrieval_query(
        request.query,
        profile=profile,
        language=lang,
    )
    try:
        retrieved_chunks = retrieve(
            query=retrieval_spec.search_text,
            top_k=8,
            min_similarity=None,
            organization_filter=retrieval_spec.organization_scope or "NSFDC",
            domain_filter=retrieval_spec.domain,
            assistance_type_filter="LOAN",
            retrieval_query=retrieval_spec,
        )
    except Exception as exc:
        print(f"[Guided] Adviser retrieval skipped: {exc}")
        return []
    return [c.scheme_id for c in _unique_retrieved_schemes(retrieved_chunks)]


def _adviser_chat_response(
    request: ChatRequest,
    profile: ChatProfile,
    session_id: str,
    *,
    retrieved_ids: list[str] | None = None,
    expected_field: str | None = "general",
) -> ChatResponse:
    lang = request.language or "en"
    mode, named = detect_adviser_mode(request.query)
    domain = profile.projectType or ("EDUCATION" if named and named[0] in EDUCATION_CREDIT_IDS else "BUSINESS")
    if named and named[0] in EDUCATION_CREDIT_IDS and mode in {EXPLAIN, COMPARE}:
        domain = "EDUCATION"
    elif not profile.projectType and _query_suggests_education(request.query):
        domain = "EDUCATION"
        profile.projectType = "EDUCATION"
    elif (
        named
        and any(sid in BUSINESS_CREDIT_IDS for sid in named)
        and (domain or "").upper() != "EDUCATION"
        and not _query_suggests_education(request.query)
    ):
        domain = "BUSINESS"
    live_ids = _retrieve_adviser_scheme_ids(request, profile, lang)
    retrieved_ids = live_ids or list(retrieved_ids or [])
    amount = _conversation_amount(profile)
    brief = build_brief(
        domain=domain,
        amount=float(amount) if amount is not None else None,
        activity=_education_course(profile) if (domain or "").upper() == "EDUCATION" else profile.activity,
        lang=lang,
        mode=mode,
        named_ids=named,
        retrieved_ids=retrieved_ids,
        income=float(profile.annualFamilyIncome) if profile.annualFamilyIncome is not None else None,
        query=request.query,
        sc_status=profile.scEligibilityStatus,
    )
    if brief.primary:
        profile.recommendedSchemeId = brief.primary.facts.scheme_id
    elif (domain or "").upper() == "AGRICULTURE":
        profile.recommendedSchemeId = None
    profile.alternativeSchemeIds = [f.facts.scheme_id for f in brief.alternatives]
    if (domain or "").upper() == "EDUCATION":
        expected_field = _education_expected_field(brief.missing, expected_field)
    _set_expected_field(profile, session_id, expected_field)
    add_turn(session_id, request.query, brief.answer)
    return ChatResponse(
        answer=brief.answer,
        language=lang,
        citations=[],
        ui_cards=adviser_ui_cards(brief, lang),
        grounding_status="GROUNDED",
        related_scheme_ids=brief.related_ids,
        response_source=ResponseSource.RAG_LLM,
        expected_field=expected_field,
        follow_ups=[brief.next_question] if brief.next_question else [],
    )


_INCOME_QUESTION_MARKERS = (
    "annual family income",
    "वार्षिक पारिवारिक आय",
    "सालाना पारिवारिक आय",
    "family income",
)
_BTECH_ITI_MEDICAL_GATE = (
    "btech, medical, nursing, iti",
    "btech, मेडिकल, नर्सिंग, iti",
    "btech, iti",
)
_DOC_REQUEST_MARKERS = (
    "document", "documents", "checklist", "papers",
    "दस्तावेज़", "दस्तावेज", "कागज़", "कागज", "डॉक्यूमेंट",
)
_PARTNER_REQUEST_MARKERS = (
    "channel partner", "partners", "partner near",
    "चैनल पार्टनर", "पार्टनर खोज", "नज़दीकी",
)
_INCOME_LANGUAGE_MARKERS = (
    "income", "family income", "annual income", "salary",
    "आय", "पारिवारिक आय", "सालाना", "वार्षिक",
)


def _is_document_request(query: str) -> bool:
    q = (query or "").strip().lower()
    return any(marker in q for marker in _DOC_REQUEST_MARKERS)


def _is_partner_request(query: str) -> bool:
    q = (query or "").strip().lower()
    return any(marker in q for marker in _PARTNER_REQUEST_MARKERS)


def _mentions_income(query: str) -> bool:
    q = (query or "").strip().lower()
    return any(marker in q for marker in _INCOME_LANGUAGE_MARKERS)


def _profile_income_note(profile: ChatProfile, lang: str) -> str:
    if profile.annualFamilyIncome is not None:
        return ""
    if lang == "hi":
        return (
            " विस्तृत eligibility जाँच के लिए Profile में वार्षिक पारिवारिक आय पूरी करना मददगार है. "
            "मैं अभी योजना recommend कर सकता हूँ।"
        )
    return (
        " For a detailed eligibility check, you can complete annual family income in Profile. "
        "I can still recommend the relevant scheme now."
    )


def _seed_chat_profile_from_persistent(profile: ChatProfile, persistent: dict) -> ChatProfile:
    """Copy Profile-owned facts into conversation state. Never overwrite a filled slot."""
    if not persistent:
        return profile
    if persistent.get("fullName") and not getattr(profile, "fullName", None):
        profile.fullName = persistent.get("fullName")
    eligibility = persistent.get("eligibility") or {}
    if profile.annualFamilyIncome is None and eligibility.get("annualFamilyIncome") is not None:
        try:
            profile.annualFamilyIncome = int(eligibility["annualFamilyIncome"])
        except (TypeError, ValueError):
            pass
    if profile.scEligibilityStatus is None and eligibility.get("scEligibilityStatus") is not None:
        profile.scEligibilityStatus = bool(eligibility["scEligibilityStatus"])
    address = persistent.get("address") or {}
    if address.get("pinCode") and not profile.pinCode:
        profile.pinCode = address.get("pinCode")
    if address.get("state") and not profile.stateCode:
        profile.stateCode = address.get("state")
    if address.get("district") and not profile.districtCode:
        profile.districtCode = address.get("district")
    coords = address.get("coordinates") or {}
    if profile.latitude is None and coords.get("latitude") is not None:
        try:
            profile.latitude = float(coords["latitude"])
            if coords.get("longitude") is not None:
                profile.longitude = float(coords["longitude"])
        except (TypeError, ValueError):
            pass
    if persistent.get("educationLevel") and not profile.educationStatus:
        profile.educationStatus = persistent.get("educationLevel")
    business = persistent.get("business") or {}
    if profile.existingBusiness is None and business.get("existingBusiness") is not None:
        profile.existingBusiness = bool(business["existingBusiness"])
    return profile


def _set_expected_field(profile: ChatProfile, session_id: str, field: str | None) -> None:
    profile.lastExpectedField = field
    update_session_profile(session_id, profile)


def _scheme_display_name(chunk, lang: str) -> str:
    sid = getattr(chunk, "scheme_id", None)
    if sid:
        try:
            meta = load_scheme(sid)
            api = meta.get("api") if isinstance(meta.get("api"), dict) else {}
            names = api.get("name") or {}
            localized = names.get(lang) or names.get("en")
            if localized:
                return str(localized)
        except Exception:
            pass
    return getattr(chunk, "scheme_name", None) or sid or "NSFDC scheme"


def _deterministic_scheme_reply(
    retrieved_chunks: list,
    lang: str,
    is_education: bool,
    is_agriculture: bool,
    activity: str | None,
    profile: ChatProfile | None = None,
) -> str | None:
    schemes = _unique_retrieved_schemes(retrieved_chunks)
    if not schemes:
        return None
    best = schemes[0]
    name = _scheme_display_name(best, lang)
    org = best.organization or "NSFDC"
    income_note = _profile_income_note(profile or ChatProfile(), lang)
    if lang == "hi":
        if is_education:
            return (
                f"आपके लिए {org} की {name} relevant है. "
                f"यह eligible professional/technical education के लिए educational loan प्रदान करती है. "
                f"आपकी saved profile information को ध्यान में रखकर मैं आपको आगे guide कर सकता हूँ."
                f"{income_note}"
            )
        if is_agriculture:
            if str(activity or "").upper() in {"", "FARMING", "AGRICULTURE", "GENERAL"}:
                return (
                    f"आप खेती/कृषि के लिए लोन की तलाश कर रहे हैं। उपलब्ध सत्यापित रिकॉर्ड में {name} मिली है. "
                    f"यह {org} की योजना है। आप किस खास खेती की गतिविधि—जैसे फसल, डेयरी या मुर्गी पालन—के लिए लोन चाहते हैं?"
                )
            return (
                f"आप खेती/कृषि के लिए लोन की तलाश कर रहे हैं। उपलब्ध सत्यापित रिकॉर्ड में {name} मिली है. "
                f"यह {org} की योजना है। अनुमानित राशि कितनी है?"
            )
        return (
            f"आपके उद्देश्य से मेल खाती सत्यापित योजना {name} मिली है. यह {org} की योजना है। "
            f"अनुमानित लागत कितनी है?"
        )
    if is_education:
        return (
            f"{org}'s {name} is relevant for your education-loan request. "
            f"It supports eligible professional/technical education. "
            f"I can guide you using your saved profile information."
            f"{income_note}"
        )
    if is_agriculture:
        if str(activity or "").upper() in {"", "FARMING", "AGRICULTURE", "GENERAL"}:
            return (
                f"You are looking for farming-related finance. I found a verified scheme: {name}. "
                f"It is an {org} scheme. Which specific farming activity do you mean, such as crop cultivation, dairy or poultry?"
            )
        return (
            f"You are looking for farming-related finance. I found a verified scheme: {name}. "
            f"It is an {org} scheme. What amount are you considering?"
        )
    return (
        f"I found a verified scheme that matches this purpose: {name} ({org}). "
        f"What is the estimated project cost?"
    )


def _exhausted_no_match_answer(lang: str, domain: str, activity: str | None) -> str:
    act = str(activity or "").upper()
    if domain == "EDUCATION":
        if lang == "hi":
            return (
                "आप शिक्षा के लिए लोन की तलाश कर रहे हैं। उपलब्ध सत्यापित रिकॉर्ड में मुझे अभी कोई शिक्षा-ऋण योजना नहीं मिली। "
                "मैं छात्रवृत्ति या कोचिंग योजना को ऋण के रूप में नहीं बताऊँगा।"
            )
        return (
            "You are looking for an education loan. I could not find a verified education-loan scheme in the available records. "
            "I will not present a scholarship or coaching scheme as a loan."
        )
    if domain == "AGRICULTURE":
        if act == "CROP_FARMING":
            if lang == "hi":
                return (
                    "आप फसल की खेती के लिए लोन की तलाश कर रहे हैं। उपलब्ध सत्यापित रिकॉर्ड में मुझे अभी कोई फसल/कृषि ऋण योजना नहीं मिली। "
                    "मैं चावल या डेयरी योजना नहीं गढ़ूँगा, और हरित व्यवसाय योजना को फसल ऋण के रूप में नहीं बताऊँगा।"
                )
            return (
                "You are looking for a crop-farming loan. I searched the agriculture records and could not confirm a verified crop/farming loan. "
                "I will not invent a rice or dairy scheme, and I will not present the Green Business Scheme as a crop loan."
            )
        if lang == "hi":
            return (
                "कृषि/खेती के लिए उपलब्ध सत्यापित रिकॉर्ड में मुझे अभी कोई मेल खाती ऋण योजना नहीं मिली। "
                "अगर आप फसल, डेयरी, मुर्गी पालन जैसी गतिविधि बताएँ, तो मैं उसी आधार पर फिर खोजूँगा।"
            )
        return (
            "I searched the agriculture records and could not confirm a verified matching loan yet. "
            "If you name the activity — for example crop cultivation, dairy, or poultry — I will search again."
        )
    if lang == "hi":
        return "दी गई जानकारी के आधार पर, मुझे अभी तक कोई मेल खाने वाली सत्यापित योजना नहीं मिली है। मैं कोई योजना गढ़ नहीं रहा हूँ।"
    return "Based on the information provided, I could not confirm a matching verified scheme yet. I will not invent a match."


def _maybe_restart_for_new_purpose(
    request: ChatRequest,
    profile: ChatProfile,
    session_id: str,
    state: ConversationState,
) -> ChatResponse | None:
    if state in {None, ConversationState.INITIAL_QUERY}:
        return None
    detection = detect_language_and_intent(request.query)
    new_type = _INTENT_TO_PROJECT.get(detection.intent or "")
    if not new_type or detection.is_low_info:
        return None
    current = profile.projectType
    purpose_changed = bool(current and current != new_type)
    restating_after_no_match = bool(profile.noVerifiedMatch)
    if not purpose_changed and not restating_after_no_match:
        return None
    if purpose_changed:
        profile.estimatedProjectCost = None
        profile.requestedLoanAmount = None
        profile.activity = None
        profile.lastExpectedField = None
        if hasattr(profile, "landHoldingAcres"):
            profile.landHoldingAcres = None
    profile.noVerifiedMatch = False
    profile.recommendedSchemeId = None
    profile.projectType = new_type
    profile.conversationState = ConversationState.INITIAL_QUERY
    update_session_profile(session_id, profile)
    return _handle_initial_query(request, profile, session_id)


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
            profile = _seed_chat_profile_from_persistent(profile, persistent)
            update_session_profile(session_id, profile)
    
    state = profile.conversationState or ConversationState.INITIAL_QUERY
    try:
        restarted = _maybe_restart_for_new_purpose(request, profile, session_id, state)
        if restarted is not None:
            return restarted
        mode, _named = detect_adviser_mode(request.query)
        if mode in {EXPLAIN, COMPARE, OPTIONS}:
            _extract_profile_data_from_query(request.query, profile, session_id, request.user_id)
            if not profile.projectType and (
                (_named and _named[0] == "nsfdc-education")
                or _query_suggests_education(request.query)
            ):
                profile.projectType = "EDUCATION"
            elif not profile.projectType:
                profile.projectType = "BUSINESS"
            profile.conversationState = profile.conversationState or ConversationState.COLLECTING_ELIGIBILITY
            return _adviser_chat_response(
                request, profile, session_id,
                retrieved_ids=profile.alternativeSchemeIds or ([profile.recommendedSchemeId] if profile.recommendedSchemeId else []),
                expected_field="general",
            )
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

        if state == ConversationState.APPLICATION_GUIDANCE:
            return _handle_application_guidance(request, profile, session_id)
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
        
    specific = extract_specific_activity(query)
    if specific:
        return {"intent": "LOAN", "activity": specific, "domain": "AGRICULTURE"}

    # Check for specific activities
    ACTIVITY_ALIASES = {
        "RICE_FARMING": [
            "chawal", "rice farming", "rice", "paddy", "धान", "चावल",
        ],
        "DAIRY_FARMING": [
            "dairy farming",
            "dairy farm",
            "milk business",
            "डेयरी फार्म",
            "डेयरी फार्मिंग",
            "डेयरी",
            "दूध का व्यवसाय",
            "पशुपालन",
            "dairy"
        ],
        "POULTRY": ["poultry", "murgi", "मुर्गी पालन", "मुर्गी"],
        "GOAT_REARING": ["goat farming", "goat", "bakri", "बकरी पालन", "बकरी"],
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
            "vyapar", "bijnes", "karkhana", "dukaan", "बिजनेस",
        ]
    }
    
    for activity, aliases in ACTIVITY_ALIASES.items():
        if any(alias in query_lower for alias in aliases):
            domain = "AGRICULTURE" if activity not in {"EDUCATION_LOAN", "GENERAL_BUSINESS", "TAILORING", "SHOP"} else (
                "EDUCATION" if activity == "EDUCATION_LOAN" else "BUSINESS"
            )
            return {"intent": "LOAN", "activity": activity, "domain": domain}

    generic_agri = ("kheti", "farming", "agriculture", "खेती", "कृषि", "krishi")
    if any(alias in query_lower for alias in generic_agri):
        return {"intent": "LOAN", "activity": None, "domain": "AGRICULTURE"}
            
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
            "AGRICULTURE": "FARMING",
            "BUSINESS": "GENERAL_BUSINESS",
            "GENERAL_LOAN": None,
        }
        activity = intent_to_activity.get(pre_detected_intent)
        if pre_detected_intent == "AGRICULTURE":
            activity = extract_specific_activity(request.query)
            data = {"intent": "LOAN", "activity": activity, "domain": "AGRICULTURE"}
        elif activity:
            data = {"intent": "LOAN", "activity": activity}
        elif pre_detected_intent == "GENERAL_LOAN":
            data = {"intent": "AMBIGUOUS_LOAN"}
    
    if data:
        if data.get("intent") == "AMBIGUOUS_LOAN":
            lang = request.language or "en"
            clarification_map = {
                "en": "I can help you find the right NSFDC loan. What is it for — education, farming, or a small business?",
                "hi": "ज़रूर। आप यह loan पढ़ाई, खेती, या business के लिए चाहते हैं?",
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
            domain = data.get("domain")
            if not activity:
                activity = extract_specific_activity(request.query)
            profile.activity = activity
            if domain == "AGRICULTURE" or (not domain and extract_specific_activity(request.query)):
                profile.projectType = "AGRICULTURE"
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
            elif domain == "BUSINESS":
                profile.projectType = "BUSINESS"

            parsed = _try_deterministic_parse(request.query, profile)
            for k, v in parsed.items():
                if hasattr(profile, k):
                    setattr(profile, k, v)
            update_session_profile(session_id, profile)
            
            # ── KEY FIX: Provide a conversational RAG-grounded first response ──
            # Instead of immediately asking for PIN code, give the user
            # relevant scheme information and THEN transition to collection.
            
            lang = request.language or "en"
            
            # Retrieve relevant scheme context
            retrieval_spec = build_retrieval_query(
                request.query,
                profile=profile,
                language=lang,
            )
            retrieved_chunks = retrieve(
                query=retrieval_spec.search_text,
                top_k=8,
                min_similarity=None,
                organization_filter=retrieval_spec.organization_scope or "NSFDC",
                domain_filter=retrieval_spec.domain,
                assistance_type_filter="LOAN",
                retrieval_query=retrieval_spec,
            )
            
            retrieved_schemes = _unique_retrieved_schemes(retrieved_chunks)
            retrieved_ids = [c.scheme_id for c in retrieved_schemes]
            is_agriculture = (profile.projectType or domain) == "AGRICULTURE"
            mode, named = detect_adviser_mode(request.query)
            brief = build_brief(
                domain=profile.projectType or domain,
                amount=float(_conversation_amount(profile)) if _conversation_amount(profile) is not None else None,
                activity=_education_course(profile) if (profile.projectType or domain) == "EDUCATION" else profile.activity,
                lang=lang,
                mode=mode,
                named_ids=named,
                retrieved_ids=retrieved_ids,
                income=float(profile.annualFamilyIncome) if profile.annualFamilyIncome is not None else None,
                query=request.query,
                sc_status=profile.scEligibilityStatus,
            )
            answer_text = brief.answer
            if brief.primary:
                profile.recommendedSchemeId = brief.primary.facts.scheme_id
            elif is_agriculture:
                profile.recommendedSchemeId = None
            elif retrieved_ids:
                profile.recommendedSchemeId = retrieved_ids[0]
            profile.alternativeSchemeIds = [f.facts.scheme_id for f in brief.alternatives]
            adviser_cards = adviser_ui_cards(brief, lang)
            related_ids = brief.related_ids or retrieved_ids[:4]
            follow_ups = [brief.next_question] if brief.next_question else []

            if profile.recommendedSchemeId:
                from app.api.scheme_loader import get_scheme_by_internal_id
                candidate_api = get_scheme_by_internal_id(profile.recommendedSchemeId)
                profile.channelPartnerRequired = bool(
                    candidate_api and candidate_api.get("channelPartnerRequired", False)
                )
            
            conversation_amount = parsed.get("requestedLoanAmount") or parsed.get("estimatedProjectCost")
            if (
                profile.projectType != "EDUCATION"
                and profile.activity
                and profile.activity not in {"BUSINESS", "AGRICULTURE", "GENERAL_BUSINESS", "FARMING", "GENERAL", None}
                and conversation_amount is not None
            ):
                profile.conversationState = ConversationState.SCHEME_RECOMMENDATION
                update_session_profile(session_id, profile)
                rec = _handle_scheme_recommendation(request, profile, session_id, is_transition=True)
                if rec:
                    rec.answer = f"{answer_text}\n\n{rec.answer}"
                    rec.ui_cards = adviser_cards or rec.ui_cards
                    rec.related_scheme_ids = related_ids or rec.related_scheme_ids
                    add_turn(session_id, request.query, rec.answer)
                    return rec

            expected = _initial_expected_field(profile, is_education)
            if is_education and not is_agriculture:
                expected = _education_expected_field(brief.missing, expected)
            profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
            _set_expected_field(profile, session_id, expected)
            add_turn(session_id, request.query, answer_text)
            return ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                ui_cards=adviser_cards,
                grounding_status="GROUNDED",
                related_scheme_ids=related_ids,
                response_source=ResponseSource.RAG_LLM,
                expected_field=expected,
                follow_ups=follow_ups,
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
            
            retrieval_spec = build_retrieval_query(
                request.query,
                profile=profile,
                language=lang,
            )
            retrieved_chunks = retrieve(
                query=retrieval_spec.search_text,
                top_k=5,
                min_similarity=None,
                organization_filter=retrieval_spec.organization_scope or "NSFDC",
                domain_filter=retrieval_spec.domain,
                assistance_type_filter="LOAN",
                retrieval_query=retrieval_spec,
            )
            
            answer_text = _build_conversational_first_response(
                activity=activity,
                is_education=is_education,
                retrieved_chunks=retrieved_chunks,
                lang=lang,
                user_query=request.query,
                domain=profile.projectType,
                profile=profile,
            )
            
            expected = _initial_expected_field(profile, is_education)
            profile.conversationState = ConversationState.COLLECTING_ELIGIBILITY
            _set_expected_field(profile, session_id, expected)
            add_turn(session_id, request.query, answer_text)
            
            return ChatResponse(
                answer=answer_text,
                language=lang,
                citations=[],
                grounding_status="GROUNDED",
                related_scheme_ids=[rc.chunk.scheme_id for rc in retrieved_chunks[:3]],
                response_source=ResponseSource.RAG_LLM,
                expected_field=expected,
            )
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"Error parsing initial query intent via LLM: {e}")
        
    # If not a loan intent, use standard RAG (route back to standard chat)
    return None


def _initial_expected_field(profile: ChatProfile, is_education: bool) -> str:
    if is_education or profile.projectType == "EDUCATION":
        if profile.requestedLoanAmount is None:
            return "requestedLoanAmount"
        if str(profile.activity or "").upper() in {"", "EDUCATION", "EDUCATION_LOAN", "GENERAL"}:
            return "activity"
        if profile.annualFamilyIncome is None:
            return "annualFamilyIncome"
        return "general"
    act = str(profile.activity or "").upper()
    if profile.projectType == "AGRICULTURE" and act in {"", "FARMING", "AGRICULTURE", "GENERAL"}:
        return "activity"
    return "estimatedProjectCost"


def _build_conversational_first_response(
    activity: str | None,
    is_education: bool,
    retrieved_chunks: list,
    lang: str,
    user_query: str,
    domain: str | None = None,
    profile: ChatProfile | None = None,
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
    is_agriculture = (domain or "").upper() == "AGRICULTURE" or (
        activity and any(kw in str(activity).lower() for kw in ["dairy", "farm", "agriculture", "kheti", "rice", "poultry", "goat"])
    )
    
    if is_education:
        purpose_desc = "education/studies"
    elif activity:
        purpose_desc = activity.lower().replace("_", " ")
    elif is_agriculture:
        purpose_desc = "farming, without a named crop or livestock type"
    else:
        purpose_desc = "business/self-employment"
    
    named_activity = bool(activity and str(activity).upper() not in {"FARMING", "AGRICULTURE", "GENERAL"})
    retrieved_ids = [c.scheme_id for c in _unique_retrieved_schemes(retrieved_chunks)]
    brief = build_brief(
        domain="EDUCATION" if is_education else ("AGRICULTURE" if is_agriculture else "BUSINESS"),
        amount=float(_conversation_amount(profile)) if profile and _conversation_amount(profile) is not None else None,
        activity=_education_course(profile) if is_education and profile else activity,
        lang=lang,
        mode=detect_adviser_mode(user_query)[0],
        named_ids=detect_adviser_mode(user_query)[1],
        retrieved_ids=retrieved_ids,
        income=float(profile.annualFamilyIncome) if profile and profile.annualFamilyIncome is not None else None,
        query=user_query,
        sc_status=profile.scEligibilityStatus if profile else None,
    )
    if brief.answer:
        return brief.answer
    grounded = _deterministic_scheme_reply(
        retrieved_chunks, lang, is_education, is_agriculture, activity, profile
    )
    if is_agriculture and str(activity or "").upper() == "CROP_FARMING" and not retrieved_chunks:
        grounded = _exhausted_no_match_answer(lang, "AGRICULTURE", "CROP_FARMING")
    system_prompt = f"""You are SAARTHI, a friendly multilingual loan assistant.
The user wants help with {purpose_desc}.
The user's actual words were: {user_query!r}

Here is verified scheme information that may be relevant:
{context_text}

Generate a NATURAL, CONVERSATIONAL advisory reply in {lang_name} that:
1. Acknowledges the user's purpose in one sentence. Do not introduce yourself as SAARTHI or सारथी.
2. If the context names a verified scheme, you MUST name that scheme and its organization and briefly say what the record supports.
3. For education loans: recommend the scheme first. Do NOT ask BTech/ITI/Medical as a forced choice. Do NOT ask annual family income. Profile already owns income; if it is missing, mention they can complete Profile rather than turning this into a form.
4. For farming: ask which farming activity they mean only if unspecified. Do not assume rice.
5. For business: you may ask estimated amount if unknown.
6. Never ask about business type if the purpose is farming or education.

Rules:
- Be warm and conversational, NOT robotic
- Do NOT use internal field names like existingBusiness, estimatedProjectCost
- Do NOT list every scheme
- Do NOT invent loan amounts, interest rates, or eligibility
- Keep it concise (3-5 sentences maximum)
- Respond ENTIRELY in {lang_name}
- Do NOT output JSON
- Do NOT say "based on retrieved context" or mention internal processes
- Do NOT mention rice, dairy, wheat, poultry, or any other specific crop/livestock unless the user's actual words named it.
- If the user only said farming/agriculture/खेती, ask which farming activity they mean. Do not assume rice.
- NEVER say that no verified scheme exists if the context above names a scheme.
- Do not present scholarships, coaching, or fellowships as loans.
- If the verified context contains no scheme, do not name Term Loan, Micro Finance, or Green Business as a substitute match.
- Do not invent that a business loan covers farming unless the retrieved text says so.
- Do not start an eligibility questionnaire. Recommendation comes before eligibility collection."""
    
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
            if not named_activity and is_agriculture:
                lowered = answer.lower()
                invented = ("rice" in lowered or "चावल" in lowered or "paddy" in lowered) and not extract_specific_activity(user_query)
                if invented:
                    answer = ""
            if answer and retrieved_chunks and _answer_denies_schemes(answer):
                answer = grounded or ""
            if answer:
                return answer
    except Exception as e:
        logger = __import__("logging").getLogger(__name__)
        logger.warning(f"LLM first response generation failed: {e}")

    if grounded:
        return grounded
    fallback_map = {
        "en": {
            "education": "NSFDC's Educational Loan Scheme is relevant for your request. It supports eligible professional/technical education. I can guide you using your saved profile.",
            "agriculture": "Are you looking for a loan for a specific farming activity, such as crop cultivation, dairy, poultry, or another agricultural activity?",
            "business": "I can help you with business financing. NSFDC offers several schemes like Micro Finance, Term Loan, and Laghu Vyavsay Yojana for different business sizes. What kind of business are you planning?",
            "agriculture": "Are you looking for a loan for a specific farming activity, such as crop cultivation, dairy, poultry, or another agricultural activity?",
            "business": "I can help you with business financing. NSFDC offers several schemes like Micro Finance, Term Loan, and Laghu Vyavsay Yojana for different business sizes. What kind of business are you planning?",
        },
        "hi": {
            "education": "आपके लिए NSFDC की Educational Loan Scheme relevant है. यह eligible professional/technical education के लिए educational loan प्रदान करती है. आपकी saved profile के आधार पर मैं आगे guide कर सकता हूँ.",
            "agriculture": "क्या आप किसी खास खेती की गतिविधि के लिए लोन चाहते हैं, जैसे फसल, डेयरी, मुर्गी पालन, या कोई और कृषि काम?",
            "business": "मैं आपको व्यवसाय के लिए वित्तीय सहायता में मदद कर सकता हूँ। NSFDC की कई योजनाएं हैं जैसे माइक्रो फाइनेंस, टर्म लोन, और लघु व्यवसाय योजना। आप किस प्रकार का व्यवसाय शुरू करना चाहते हैं?",
            "agriculture": "क्या आप किसी खास खेती की गतिविधि के लिए लोन चाहते हैं, जैसे फसल, डेयरी, मुर्गी पालन, या कोई और कृषि काम?",
            "business": "मैं आपको व्यवसाय के लिए वित्तीय सहायता में मदद कर सकता हूँ। NSFDC की कई योजनाएं हैं जैसे माइक्रो फाइनेंस, टर्म लोन, और लघु व्यवसाय योजना। आप किस प्रकार का व्यवसाय शुरू करना चाहते हैं?",
        },
        "mr": {
            "education": "नक्कीच, मी तुम्हाला शैक्षणिक कर्जामध्ये मदत करू शकतो. कोणत्या कोर्ससाठी तुम्ही विचार करत आहात?",
            "agriculture": "तुम्हाला कोणत्या शेती कामासाठी कर्ज हवे आहे — पीक, दुग्धव्यवसाय, कुक्कुटपालन किंवा इतर कृषी काम?",
            "business": "मी तुम्हाला व्यवसायासाठी आर्थिक मदतीत मदत करू शकतो. तुम्ही कोणता व्यवसाय सुरू करणार आहात?"
        },
        "bn": {
            "education": "আমি আপনাকে শিক্ষা ঋণের বিষয়ে সাহায্য করতে পারি। আপনি কোন কোর্সটি করতে চান?",
            "agriculture": "আপনি কি নির্দিষ্ট কোনো কৃষিকাজের জন্য ঋণ চান, যেমন ফসল, দুগ্ধ, মুরগি পালন, বা অন্য কোনো কৃষি কাজ?",
            "business": "আমি আপনাকে ব্যবসার জন্য আর্থিক সহায়তা পেতে সাহায্য করতে পারি। আপনি কি ধরণের ব্যবসা শুরু করতে চান?"
        },
        "ta": {
            "education": "நான் உங்களுக்கு கல்வி கடன்களுக்கு உதவ முடியும். நீங்கள் எந்த படிப்பை படிக்க விரும்புகிறீர்கள்?",
            "agriculture": "பயிர், பால் பண்ணை, கோழி வளர்ப்பு அல்லது வேறு விவசாய வேலை போன்ற குறிப்பிட்ட விவசாய நடவடிக்கைக்காகவா கடன் வேண்டும்?",
            "business": "வணிக நிதிக்கு நான் உங்களுக்கு உதவ முடியும். நீங்கள் என்ன வகையான வணிகத்தைத் தொடங்க திட்டமிட்டுள்ளீர்கள்?"
        },
        "te": {
            "education": "నేను మీకు విద్యా రుణాలతో సహాయం చేయగలను. మీరు ఏ కోర్సు చదవాలనుకుంటున్నారు?",
            "agriculture": "పంట, పాడి, కోడి పెంపకం లేదా ఇతర వ్యవసాయ పని వంటి నిర్దిష్ట వ్యవసాయ కార్యకలాపం కోసమా రుణం కావాలి?",
            "business": "వ్యాపార ఆర్థిక సహాయంతో నేను మీకు సహాయం చేయగలను. మీరు ఏ రకమైన వ్యాపారాన్ని ప్రారంభించాలనుకుంటున్నారు?"
        }
    }
    
    category = "education" if is_education else ("agriculture" if is_agriculture else "business")
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
        "chawal": "RICE_FARMING", "चावल": "RICE_FARMING",
        "wheat": "WHEAT_FARMING", "गेहूं": "WHEAT_FARMING", "gehun": "WHEAT_FARMING",
        "vegetable": "VEGETABLE_FARMING", "vegetables": "VEGETABLE_FARMING",
        "सब्जी": "VEGETABLE_FARMING", "sabji": "VEGETABLE_FARMING",
        "fruit": "HORTICULTURE", "fruits": "HORTICULTURE", "फल": "HORTICULTURE", "horticulture": "HORTICULTURE",
        "dairy": "DAIRY_FARMING", "milk": "DAIRY_FARMING", "डेयरी": "DAIRY_FARMING", "दूध": "DAIRY_FARMING",
        "poultry": "POULTRY", "murgi": "POULTRY", "मुर्गी": "POULTRY",
        "fish": "FISHERY", "fishing": "FISHERY", "मछली": "FISHERY",
        "goat": "GOAT_REARING", "sheep": "GOAT_REARING", "बकरी": "GOAT_REARING", "bakri": "GOAT_REARING",
        "pig": "PIG_REARING", "सूअर": "PIG_REARING",
        # Business / Trade — longer / more specific phrases must win over "shop".
        "mobile repair": "REPAIR_WORKSHOP",
        "repair shop": "REPAIR_WORKSHOP",
        "workshop": "REPAIR_WORKSHOP",
        "mechanic": "REPAIR_WORKSHOP",
        "repair": "REPAIR_WORKSHOP",
        "shop": "SMALL_RETAIL", "dukaan": "SMALL_RETAIL", "दुकान": "SMALL_RETAIL",
        "tailoring": "TAILORING", "silai": "TAILORING", "सिलाई": "TAILORING",
        "handicraft": "HANDICRAFT", "craft": "HANDICRAFT", "हस्तशिल्प": "HANDICRAFT",
        "beauty": "BEAUTY_PARLOUR", "salon": "BEAUTY_PARLOUR",
        "transport": "TRANSPORT", "auto": "TRANSPORT", "cab": "TRANSPORT",
        "catering": "CATERING", "food": "FOOD_PROCESSING",
        "fasal": "CROP_FARMING", "फसल": "CROP_FARMING", "crop": "CROP_FARMING",
        "crops": "CROP_FARMING",
    }
    if profile.activity in _VAGUE_ACTIVITIES and not is_transition:
        q_low = request.query.strip().lower()
        for kw, mapped in sorted(_ACTIVITY_SHORT_MAP.items(), key=lambda item: -len(item[0])):
            if kw in q_low:
                profile.activity = mapped
                update_session_profile(session_id, profile)
                print(f"[Guided] Resolved short activity answer '{kw}' → {mapped}")
                break

    _AGRI_GENERIC = {"FARMING", "AGRICULTURE"}

    # Conversation must not become a profile form. Profile owns income/SC.
    # Education retrieval is not gated on course, fee, or income.
    missing_fields = []

    if _is_document_request(request.query) and profile.recommendedSchemeId:
        profile.conversationState = ConversationState.DOCUMENT_PREPARATION
        update_session_profile(session_id, profile)
        return _handle_document_preparation(request, profile, session_id)
    if _is_partner_request(request.query) and profile.recommendedSchemeId:
        profile.conversationState = ConversationState.PARTNER_SEARCH
        update_session_profile(session_id, profile)
        return _handle_partner_search(request, profile, session_id, is_transition=True)

    if not missing_fields:
        if profile.noVerifiedMatch:
            rec = _handle_scheme_recommendation(request, profile, session_id, is_transition=True)
            if rec and not profile.noVerifiedMatch:
                return rec
            lang = request.language or "en"
            domain = "EDUCATION" if profile.projectType == "EDUCATION" else (
                "AGRICULTURE" if profile.projectType == "AGRICULTURE" else "BUSINESS"
            )
            return ChatResponse(
                answer=_exhausted_no_match_answer(lang, domain, profile.activity),
                language=lang,
                citations=[],
                grounding_status="GROUNDED",
                response_source=ResponseSource.CLARIFICATION,
            )
        if profile.recommendedSchemeId:
            return _acknowledge_follow_up(request, profile, session_id)
        profile.conversationState = ConversationState.SCHEME_RECOMMENDATION
        update_session_profile(session_id, profile)
        return _handle_scheme_recommendation(request, profile, session_id, is_transition=True)
        
    # Ask the FIRST missing field
    next_question = missing_fields[0]
    
    lang = request.language or "en"
    questions_map = {
        "en": {
            "Specific Activity": "Could you tell me what specific kind of work or farming you want to do?",
            "Course / education level": "Which course are you pursuing?",
            "PIN Code": "I need your 6-digit PIN code to find accurate schemes and partners. Please update your PIN in your Profile.",
            "Is this a new business or an existing business?": "Is this a new business or an existing business?",
            "Estimated Project Cost": "What is the estimated total project cost?",
            "Course Fee": "What is the total estimated course fee?",
            "Annual Family Income": "To check the scheme's income condition, what is your annual family income?",
            "SC Category Confirmation": "NSFDC credit schemes are for Scheduled Caste applicants. Do you belong to the SC category?"
        },
        "hi": {
            "Specific Activity": "आप किस प्रकार का काम या खेती शुरू करना चाहते हैं?",
            "Course / education level": "आप कौन-सा course कर रहे हैं?",
            "PIN Code": "सटीक योजनाएं और भागीदार खोजने के लिए मुझे आपके 6 अंकों के पिन कोड की आवश्यकता है। कृपया अपने प्रोफाइल में अपना पिन अपडेट करें।",
            "Is this a new business or an existing business?": "क्या यह नया व्यवसाय है या आपका पहले से चल रहा व्यवसाय है?",
            "Estimated Project Cost": "इस परियोजना की अनुमानित कुल लागत कितनी है?",
            "Course Fee": "कोर्स की अनुमानित कुल फीस कितनी है?",
            "Annual Family Income": "योजना की आय शर्त जाँचने के लिए आपकी वार्षिक पारिवारिक आय कितनी है?",
            "SC Category Confirmation": "NSFDC की ऋण योजनाएँ अनुसूचित जाति के आवेदकों के लिए हैं। क्या आप SC श्रेणी से हैं?"
        },
        "mr": {
            "Specific Activity": "तुम्हाला कोणता विशिष्ट प्रकारचा व्यवसाय किंवा शेती करायची आहे?",
            "Course / education level": "हे कर्ज कोणत्या कोर्स किंवा शिक्षणासाठी आहे — उदा. BTech, medical, nursing, ITI, 12th?",
            "PIN Code": "अचूक योजना आणि भागीदार शोधण्यासाठी मला तुमचा 6-अंकी पिन कोड आवश्यक आहे. कृपया तुमच्या प्रोफाइलमध्ये तुमचा पिन अपडेट करा.",
            "Is this a new business or an existing business?": "हा नवीन व्यवसाय आहे की जुना?",
            "Estimated Project Cost": "अंदाजित प्रकल्प खर्च किती आहे?",
            "Course Fee": "कोर्सची अंदाजित एकूण फी किती आहे?"
        },
        "bn": {
            "Specific Activity": "আপনি নির্দিষ্ট কি ধরনের কাজ বা চাষাবাদ করতে চান তা কি বলতে পারবেন?",
            "Course / education level": "এই ঋণ কোন কোর্স বা পড়ার জন্য — যেমন BTech, medical, nursing, ITI, 12th?",
            "PIN Code": "সঠিক স্কিম এবং পার্টনার খুঁজে পেতে আমার আপনার ৬-সংখ্যার পিন কোড দরকার। অনুগ্রহ করে আপনার প্রোফাইলে পিন আপডেট করুন।",
            "Is this a new business or an existing business?": "এটি কি একটি নতুন ব্যবসা না বিদ্যমান ব্যবসা?",
            "Estimated Project Cost": "আনুমানিক প্রকল্প ব্যয় কত?",
            "Course Fee": "কোর্সের আনুমানিক মোট ফি কত?"
        },
        "ta": {
            "Specific Activity": "நீங்கள் எந்த வகையான குறிப்பிட்ட வேலை அல்லது விவசாயம் செய்ய விரும்புகிறீர்கள் என்பதை என்னிடம் கூற முடியுமா?",
            "Course / education level": "இந்த கடன் எந்த பாடம் அல்லது கல்வி நிலைக்காக — உதா. BTech, medical, nursing, ITI, 12th?",
            "PIN Code": "சரியான திட்டங்கள் மற்றும் கூட்டாளர்களைக் கண்டறிய உங்கள் 6 இலக்க பின் குறியீடு எனக்குத் தேவை. தயவுசெய்து உங்கள் சுயவிவரத்தில் உங்கள் பின்னைப் புதுப்பிக்கவும்.",
            "Is this a new business or an existing business?": "இது புதிய தொழிலா அல்லது ஏற்கனவே உள்ள தொழிலா?",
            "Estimated Project Cost": "மதிப்பிடப்பட்ட திட்ட செலவு என்ன?",
            "Course Fee": "மதிப்பிடப்பட்ட மொத்த பாட கட்டணம் என்ன?"
        },
        "te": {
            "Specific Activity": "మీరు ఏ నిర్దిష్ట రకమైన పని లేదా వ్యవసాయం చేయాలనుకుంటున్నారో నాకు చెప్పగలరా?",
            "Course / education level": "ఈ రుణం ఏ కోర్సు లేదా చదువు కోసం — ఉదా. BTech, medical, nursing, ITI, 12th?",
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
        "Course / education level": "activity",
        "Specific Activity": "activity",
        "Annual Family Income": "annualFamilyIncome",
        "SC Category Confirmation": "scEligibilityStatus",
    }
    expected_field = FIELD_MAP.get(next_question, "general")
    _set_expected_field(profile, session_id, expected_field)
        
    return ChatResponse(
        answer=answer_text,
        language=request.language or "en",
        citations=[],
        ui_cards=ui_cards,
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM,
        expected_field=expected_field
    )


def _acknowledge_follow_up(request: ChatRequest, profile: ChatProfile, session_id: str) -> ChatResponse:
    """Keep conversation context and re-score NSFDC options from verified facts."""
    return _adviser_chat_response(
        request,
        profile,
        session_id,
        retrieved_ids=profile.alternativeSchemeIds or ([profile.recommendedSchemeId] if profile.recommendedSchemeId else []),
        expected_field="general",
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


def _collect_scaled_amounts(text: str) -> list[tuple[int, int]]:
    """Return (start_index, rupee_value) for each scaled amount in text."""
    found: list[tuple[int, int]] = []
    seen_spans: set[tuple[int, int]] = set()
    for m in _COST_PATTERN.finditer(text):
        raw = m.group(1).replace(",", "")
        try:
            amount = float(raw)
        except ValueError:
            continue
        suffix_text = m.group(0).lower()
        has_scale = any(s in suffix_text for s in ("lakh", "lac", "लाख", "thousand", "हजार")) or suffix_text.endswith("k")
        if "lakh" in suffix_text or "lac" in suffix_text or "लाख" in suffix_text:
            amount *= 100_000
        elif "thousand" in suffix_text or "हजार" in suffix_text or suffix_text.endswith("k"):
            amount *= 1_000
        if amount < 1000 and not has_scale:
            continue
        span = (m.start(), m.end())
        if span in seen_spans:
            continue
        seen_spans.add(span)
        found.append((m.start(), int(amount)))
    return found


def _try_deterministic_parse(query: str, profile: ChatProfile) -> dict:
    """
    Attempt to extract profile fields from a query WITHOUT calling the LLM.
    Returns a dict of {field_name: value} for any fields it could determine.
    Returns an empty dict if the query is ambiguous and needs LLM processing.
    """
    q = query.strip().lower()
    query_norm = normalize_indic_digits(q)
    updates: dict = {}

    # A bare yes/no is SC confirmation only when that was the asked slot.
    if profile.scEligibilityStatus is None and getattr(profile, "lastExpectedField", None) == "scEligibilityStatus":
        normalized_answer = q.strip().rstrip(".!?")
        if normalized_answer in _YES_ANSWERS:
            updates["scEligibilityStatus"] = True
        elif normalized_answer in _NO_ANSWERS:
            updates["scEligibilityStatus"] = False

    # Check New/Existing business answer — never for education journeys.
    if profile.projectType != "EDUCATION" and profile.existingBusiness is None:
        # Add extra mappings from user request
        new_biz = _NEW_BUSINESS_ANSWERS | {"नया व्यवसाय", "नया बिजनेस", "नई शुरुआत", "शुरू करना है", "पहले से नहीं है"}
        old_biz = _EXISTING_BUSINESS_ANSWERS | {"पुराना व्यवसाय", "मौजूदा व्यवसाय", "पहले से व्यवसाय", "पहले से चल रहा है", "पहले से है"}
        
        negated_existing = any(
            phrase in q
            for phrase in (
                "don't have an existing",
                "dont have an existing",
                "do not have an existing",
                "don't have a business",
                "do not have a business",
                "no existing business",
                "not an existing business",
                "पहले से नहीं है",
            )
        )
        if negated_existing:
            updates["existingBusiness"] = False
        elif any(term in q for term in new_biz):
            updates["existingBusiness"] = False
        elif any(term in q for term in old_biz):
            updates["existingBusiness"] = True

    # Explicit PIN change intent check
    change_pin_phrases = ["change", "update", "new pin", "instead", "बदलना", "नया पिन", "दूसरा", "बदलकर"]
    is_explicit_change = any(p in q for p in change_pin_phrases)

    # Check for PIN code (6-digit number starting with 1-9)
    # Be careful not to match large loan amounts like 500000 as a PIN code.
    if profile.pinCode is None or is_explicit_change:
        pins = _PIN_PATTERN.findall(query_norm)
        if pins:
            pin_val = int(pins[0])
            if pin_val % 10000 != 0 or is_explicit_change:
                updates["pinCode"] = pins[0]

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

    acre_match = None
    word_acre = None
    if profile.projectType != "EDUCATION":
        acre_match = __import__("re").search(
            r"(\d+(?:\.\d+)?)\s*(acre|acres|एकड़|एकड)\b",
            query_norm,
            __import__("re").IGNORECASE,
        )
        if not acre_match:
            for word, num in _WORD_NUMS.items():
                if __import__("re").search(
                    rf"{__import__('re').escape(word)}\s*(acre|acres|एकड़|एकड)\b",
                    query_norm,
                    __import__("re").IGNORECASE,
                ):
                    word_acre = float(num)
                    break
        if acre_match or word_acre is not None:
            try:
                updates["landHoldingAcres"] = float(acre_match.group(1)) if acre_match else word_acre
            except ValueError:
                pass
            if profile.activity:
                updates["activity"] = profile.activity

    looks_like_land = bool(acre_match) or word_acre is not None
    if not looks_like_land and "pinCode" not in updates:
        expected = getattr(profile, "lastExpectedField", None) or ""
        is_income_answer = expected == "annualFamilyIncome" or _mentions_income(q)
        if expected in {"estimatedProjectCost", "courseFee", "requestedLoanAmount"} and not _mentions_income(q):
            is_income_answer = False
        fee_markers = any(
            marker in q
            for marker in ("course fee", "tuition", "फीस", "fees")
        )
        loanish = profile.projectType == "EDUCATION" or any(
            marker in q for marker in ("loan", "लोन", "education", "study", "padhai", "पढ़ाई", "fees", "फीस")
        )
        scaled = _collect_scaled_amounts(query_norm)
        if is_income_answer and loanish and len(scaled) >= 2:
            income_hits = [query_norm.find(m) for m in ("family income", "annual income", "income", "आय") if m in query_norm]
            loan_hits = [
                query_norm.find(m)
                for m in ("loan", "लोन", "education", "study", "padhai", "पढ़ाई", "fees", "फीस", "chahiye")
                if m in query_norm
            ]
            income_pos = min(income_hits) if income_hits else 0
            loan_pos = min(loan_hits) if loan_hits else len(query_norm)
            income_amt = min(scaled, key=lambda item: abs(item[0] - income_pos))
            loan_amt = min((item for item in scaled if item != income_amt), key=lambda item: abs(item[0] - loan_pos), default=None)
            updates["annualFamilyIncome"] = income_amt[1]
            if loan_amt:
                updates["requestedLoanAmount" if profile.projectType == "EDUCATION" or loanish else "estimatedProjectCost"] = loan_amt[1]
        else:
            # Education amounts are requested loan, not business project cost.
            if is_income_answer:
                target_amount_field = "annualFamilyIncome"
            elif profile.projectType == "EDUCATION":
                target_amount_field = "estimatedProjectCost" if fee_markers else "requestedLoanAmount"
            else:
                target_amount_field = "estimatedProjectCost"
            word_amount = _resolve_word_amount(query_norm)
            if word_amount:
                updates[target_amount_field] = word_amount

            stripped = __import__("re").sub(
                r"(?:project cost|cost|estimate|budget|amount|approximately|around|about|लागत|खर्च|budget)\s*[:=]?\s*",
                "",
                query_norm,
                flags=__import__("re").IGNORECASE,
            )

            if target_amount_field not in updates:
                bare_number_match = __import__("re").search(r"^\s*(\d[\d,]*)\s*$", query_norm)
                if bare_number_match:
                    raw = bare_number_match.group(1).replace(",", "")
                    try:
                        amount = int(raw)
                        if amount >= 1000:
                            updates[target_amount_field] = amount
                    except ValueError:
                        pass

            if target_amount_field not in updates:
                for m in _COST_PATTERN.finditer(stripped):
                    raw = m.group(1).replace(",", "")
                    try:
                        amount = float(raw)
                        suffix_text = m.group(0).lower()
                        has_scale = any(s in suffix_text for s in ("lakh", "lac", "लाख", "thousand", "हजार")) or suffix_text.endswith("k")
                        if "lakh" in suffix_text or "lac" in suffix_text or "लाख" in suffix_text:
                            amount *= 100_000
                        elif "thousand" in suffix_text or "हजार" in suffix_text or suffix_text.endswith("k"):
                            amount *= 1_000
                        if amount < 1000 and not has_scale:
                            continue
                        updates[target_amount_field] = int(amount)
                        break
                    except ValueError:
                        pass

    sc_positive = (
        "i am sc", "scheduled caste", "sc category", "मैं sc", "अनुसूचित जाति",
        "haan sc", "yes sc",
    )
    sc_negative = ("not sc", "not scheduled caste", "sc नहीं", "अनुसूचित जाति नहीं")
    if any(marker in q for marker in sc_negative):
        updates["scEligibilityStatus"] = False
    elif any(marker in q for marker in sc_positive):
        updates["scEligibilityStatus"] = True

    _CITY_HINTS = {
        "jaipur": ("RJ", "Jaipur"),
        "जयपुर": ("RJ", "Jaipur"),
    }
    for city, (st, district) in _CITY_HINTS.items():
        if city in q:
            updates["stateCode"] = st
            updates["districtCode"] = district
            break

    return updates


_PROFILE_SAVE_RE = re.compile(
    r"(?:profile|प्रोफाइल|प्रोफ़ाइल).{0,48}(?:save|update|सेव|अपडेट|डाल|कर\s*दो)"
    r"|(?:save|update|सेव).{0,48}(?:profile|प्रोफाइल|प्रोफ़ाइल)"
    r"|remember.{0,32}(?:my\s+)?(?:income|profile|प्रोफाइल|प्रोफ़ाइल)",
    re.IGNORECASE,
)


def _explicit_profile_save_request(query: str) -> bool:
    """True only when the user asks to write conversation facts into Profile."""
    return bool(_PROFILE_SAVE_RE.search(query or ""))


def _extract_profile_data_from_query(query: str, profile: ChatProfile, session_id: str, user_id: str = None):
    # 1. Try deterministic parsing first (no LLM call, no latency)
    deterministic = _try_deterministic_parse(query, profile)
    
    def _sync_persistent_fields(updates: dict):
        if not user_id:
            return
        if not _explicit_profile_save_request(query):
            return
        merged = dict(updates or {})
        if "annualFamilyIncome" not in merged and profile.annualFamilyIncome is not None:
            merged["annualFamilyIncome"] = profile.annualFamilyIncome
        if "scEligibilityStatus" not in merged and profile.scEligibilityStatus is not None:
            merged["scEligibilityStatus"] = profile.scEligibilityStatus
        persistable = {
            k: merged[k]
            for k in ("pinCode", "fullName", "annualFamilyIncome", "scEligibilityStatus")
            if k in merged
        }
        if not persistable:
            return
        from app.services.storage import get_profile_store
        store = get_profile_store()
        persistent = store.get(user_id) or {}

        if "pinCode" in persistable:
            if "address" not in persistent:
                persistent["address"] = {}
            persistent["address"]["pinCode"] = persistable["pinCode"]
            print(f"[PROFILE] Saving PIN: {persistable['pinCode']}")

        if "fullName" in persistable:
            persistent["fullName"] = persistable["fullName"]
            print(f"[PROFILE] Saving Name: {persistable['fullName']}")

        if "annualFamilyIncome" in persistable or "scEligibilityStatus" in persistable:
            eligibility = persistent.get("eligibility") or {}
            if "annualFamilyIncome" in persistable:
                eligibility["annualFamilyIncome"] = persistable["annualFamilyIncome"]
            if "scEligibilityStatus" in persistable:
                eligibility["scEligibilityStatus"] = persistable["scEligibilityStatus"]
            persistent["eligibility"] = eligibility

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

    if _explicit_profile_save_request(query):
        _sync_persistent_fields({})
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
Available fields: fullName (string), stateCode (string), districtCode (string), pinCode (string), existingBusiness (bool), estimatedProjectCost (int), requestedLoanAmount (int), annualFamilyIncome (int), activity (string).
For education loans, put a bare amount such as "2 lakh" in requestedLoanAmount, not estimatedProjectCost or annualFamilyIncome.
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
    if not is_transition:
        _extract_profile_data_from_query(request.query, profile, session_id, request.user_id)
        profile = get_session_profile(session_id)
        if _is_document_request(request.query):
            profile.conversationState = ConversationState.DOCUMENT_PREPARATION
            update_session_profile(session_id, profile)
            return _handle_document_preparation(request, profile, session_id)
        if _is_partner_request(request.query):
            profile.conversationState = ConversationState.PARTNER_SEARCH
            update_session_profile(session_id, profile)
            return _handle_partner_search(request, profile, session_id, is_transition=True)
        if profile.recommendedSchemeId:
            return _acknowledge_follow_up(request, profile, session_id)

    profile.conversationState = ConversationState.SCHEME_RECOMMENDATION
    update_session_profile(session_id, profile)
    return _adviser_chat_response(
        request,
        profile,
        session_id,
        retrieved_ids=profile.alternativeSchemeIds or ([profile.recommendedSchemeId] if profile.recommendedSchemeId else []),
        expected_field="general",
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
    
    req_by_scheme: list[str] = []
    req_by_partner: list[str] = []
    recommended: list[str] = []
    if profile.recommendedSchemeId:
        try:
            scheme = load_scheme(profile.recommendedSchemeId)
            api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
            for document in api.get("documentsRequired") or []:
                if isinstance(document, dict):
                    label = document.get(lang) or document.get("en")
                else:
                    label = str(document)
                if label:
                    req_by_scheme.append(str(label))
        except Exception as exc:
            print(f"[Guided] Could not load grounded documents: {exc}")
    
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
        **({recommended[0]: "BUSINESS_PLAN"} if recommended else {}),
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


def _handle_application_guidance(
    request: ChatRequest,
    profile: ChatProfile,
    session_id: str,
) -> ChatResponse:
    lang = (request.language or "en").strip().lower()
    scheme = load_scheme(profile.recommendedSchemeId) if profile.recommendedSchemeId else {}
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    application_url = api.get("applicationUrl")
    official_url = api.get("officialUrl") or scheme.get("source_url")
    if lang == "hi":
        answer = (
            "अपने सत्यापित योजना दस्तावेज़ों के साथ राज्य चैनलाइजिंग एजेंसी के जिला कार्यालय में आवेदन करें। "
            "ऑनलाइन आवेदन और स्थिति देखने के लिए आधिकारिक PM-SURAJ पोर्टल का उपयोग किया जा सकता है।"
        )
    else:
        answer = (
            "Apply with the confirmed scheme documents through the district office of your State "
            "Channelizing Agency. The official PM-SURAJ portal can be used for online submission "
            "and status tracking."
        )
    if application_url:
        answer += f" {application_url}"
    elif official_url:
        answer += f" {official_url}"
    profile.conversationState = ConversationState.COMPLETED
    update_session_profile(session_id, profile)
    return ChatResponse(
        answer=answer,
        language=lang,
        citations=[],
        grounding_status="GROUNDED",
        response_source=ResponseSource.RAG_LLM,
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
            response_source=ResponseSource.RAG_LLM,
            expected_field="pinCode",
        )
        
    from app.rag.partner_repo import get_partner_repo
    repo = get_partner_repo()
    
    if profile.latitude is not None and profile.longitude is not None:
        partners = []
        for radius in (25.0, 50.0, 100.0):
            partners = repo.search_nearby(
                latitude=profile.latitude,
                longitude=profile.longitude,
                radius_km=radius,
                scheme_id=profile.recommendedSchemeId,
            )
            if partners:
                break
    else:
        partners = repo.search_by_pincode_with_expansion(
            pincode=profile.pinCode,
            scheme_id=profile.recommendedSchemeId,
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
        if p.get("distance_km") is not None:
            answer_text = found_map.get(lang, found_map["en"]).format(dist=p.get("distance_km"))
        elif lang == "hi":
            answer_text = "मुझे आपके पिन कोड/जिले की सेवा करने वाली एक सत्यापित चैनल एजेंसी मिली है। सत्यापित निर्देशांक न होने के कारण मैं इसे पास की एजेंसी या कोई दूरी नहीं बता सकता।"
        else:
            answer_text = "I found a verified channel agency serving your PIN/district. Verified coordinates are unavailable, so I cannot describe it as nearby or provide a distance."
        answer_text += (
            " आवेदन के लिए अपने जाति, आय और KYC प्रमाण तथा योजना-विशिष्ट दस्तावेज़ लेकर जाएँ; "
            "आप PM-SURAJ पोर्टल पर भी आवेदन ट्रैक कर सकते हैं।"
            if lang == "hi"
            else " Take the confirmed scheme documents plus caste, income and KYC proof; you can also submit and track the application through the PM-SURAJ portal."
        )
    else:
        answer_text = not_found_map.get(lang, not_found_map["en"])
        answer_text += (
            " आप PM-SURAJ पोर्टल पर ऑनलाइन आवेदन कर सकते हैं या अपनी राज्य चैनलाइजिंग एजेंसी के जिला कार्यालय से संपर्क कर सकते हैं।"
            if lang == "hi"
            else " You can still apply online through PM-SURAJ or contact the district office of your State Channelizing Agency."
        )
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
