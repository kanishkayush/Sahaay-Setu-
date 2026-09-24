import json
import logging
import os
from typing import Any

import litellm

from app.rag.retriever import RetrievedChunk
from app.schemas.chat import ChatRequest, ChatResponse, ResponseSource
from app.schemas.explanation import GroundingStatus, SourceCitation
from app.schemas.assistant import FrontendCitation
from app.eligibility_engine import evaluate_all_schemes
from app.recommendation_engine import generate_recommendations

logger = logging.getLogger(__name__)

def _llm_model() -> str:
    model = os.environ.get("LLM_MODEL")
    if not model:
        raise RuntimeError("LLM_MODEL environment variable is not set.")
    return model

_CHAT_OUTPUT_SCHEMA = """
{
  "language": "<language_code>",
  "answer": "<helpful conversational answer in the requested language>",
  "citations": [
    {"source_id": "<only actually used sources>", "section": "<only actually used sources>"}
  ],
  "grounding_status": "GROUNDED",
  "related_scheme_ids": ["<scheme_id_1>", "<scheme_id_2>"]
}
"""

def _build_allowed_citations(chunks: list[RetrievedChunk]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    allowed: list[dict[str, str]] = []
    for rc in chunks:
        key = (rc.chunk.source_id, rc.chunk.section)
        if key not in seen:
            seen.add(key)
            allowed.append({"source_id": rc.chunk.source_id, "section": rc.chunk.section})
    return allowed

def _validate_citations(
    generated: list[SourceCitation],
    allowed: list[dict[str, str]],
) -> list[SourceCitation]:
    allowed_set = {(c["source_id"], c["section"]) for c in allowed}
    return [c for c in generated if (c.source_id, c.section) in allowed_set]

def _build_chat_prompt(
    query: str,
    chunks: list[RetrievedChunk],
    allowed_citations: list[dict[str, str]],
    eligibility_facts: dict[str, Any] | None,
    language_pref: str | None,
    chat_history: str | None = None
) -> list[dict[str, str]]:
    
    lang_map = {
        "en": "English",
        "hi": "Hindi (हिन्दी)",
        "mr": "Marathi (मराठी)",
        "bn": "Bengali (বাংলা)",
        "ta": "Tamil (தமிழ்)",
        "te": "Telugu (తెలుగు)"
    }
    lang_name = lang_map.get(language_pref, language_pref) if language_pref else None

    lang_rule = (
        f"7. RESPONSE LANGUAGE: {lang_name}. You MUST answer entirely in {lang_name}. "
        f"Do not switch to English. Do not translate the user's question into English in the final response."
    ) if lang_name else "7. Respond naturally in the same language or language style as the user's query."

    system_prompt = f"""You are SAARTHI, a multilingual assistant for NSFDC scheme information.

SYSTEM INSTRUCTIONS
1. You may only state scheme facts supported by Retrieved knowledge context or Deterministic eligibility data.
2. Never calculate, guess, or infer personal eligibility independently.
3. If the user asks whether they personally qualify and deterministic eligibility data is unavailable, clearly state that eligibility cannot be confirmed without the required information.
4. Do not mention schemes, loan amounts, interest rates, or requirements that are not present in the retrieved context.
5. If the retrieved context does not support the answer, you must clearly say that you do not have enough verified information, naturally expressed in the user's language.
6. Focus only on NSFDC-related financial schemes and educational assistance. If a query is unrelated to this domain, politely redirect the user toward the supported domain.
{lang_rule}
8. Return ONLY a valid JSON object matching the schema. Do not write any internal thought process, reasoning, or prose outside the JSON.
9. SCHEME RECOMMENDATION RULE: When providing a recommendation, you MUST recommend the EXACT scheme name from the Deterministic Eligibility Facts (e.g., 'top_recommendation') or Retrieved context. Do not recommend just a category (like 'Term Loan' or 'Micro Finance'). 
10. RECOMMENDATION FORMAT: If a specific scheme is recommended, the "answer" string MUST clearly state the Recommended Scheme, Category, and Why it fits, written naturally in the requested language.
11. If no exact scheme can be confidently determined, the "answer" string MUST clearly explain the suitable financing category and what specific information is missing, written naturally in the requested language.
"""

    history_section = ""
    if chat_history:
        history_section = f"\nCONVERSATION HISTORY:\n{chat_history}\n"

    retrieved_text = ""
    for i, rc in enumerate(chunks, 1):
        retrieved_text += f"\n--- SOURCE {i} ---\n"
        retrieved_text += f"Scheme: {rc.chunk.scheme_name} ({rc.chunk.scheme_id})\n"
        retrieved_text += f"Section: {rc.chunk.section}\n"
        retrieved_text += f"source_id: {rc.chunk.source_id}\n"
        retrieved_text += f"Content:\n{rc.chunk.text}\n"

    eligibility_section = ""
    if eligibility_facts:
        eligibility_section = f"""
DETERMINISTIC ELIGIBILITY FACTS (provided for the user):
{json.dumps(eligibility_facts, indent=2, ensure_ascii=False)}
"""
    else:
        eligibility_section = "\nDETERMINISTIC ELIGIBILITY FACTS: None provided.\n"

    comparison_rule = ""
    if "अंतर" in query or "compare" in query.lower() or "difference" in query.lower() or "vs" in query.lower():
        comparison_rule = "\nCOMPARISON RULE: Since the user asked for a comparison, structure your answer to explicitly compare Purpose, Loan Amount, Interest, and Repayment based strictly on the retrieved context. Missing data should be stated as 'इस जानकारी के लिए उपलब्ध संदर्भ में स्पष्ट विवरण नहीं मिला।' (or equivalent in the requested language)."

    user_prompt = f"""{history_section}
CURRENT USER QUESTION: {query}
{eligibility_section}
RETRIEVED VERIFIED KNOWLEDGE (only source; never invent facts):
{retrieved_text}

OUTPUT RULES:{comparison_rule}
ALLOWED CITATIONS (use only these; do not invent):
{json.dumps(allowed_citations, ensure_ascii=False)}

OUTPUT SCHEMA:
{_CHAT_OUTPUT_SCHEMA}

Return only the JSON now."""

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

def generate_chat_answer(
    request: ChatRequest,
    retrieved_chunks: list[RetrievedChunk],
    chat_history: str | None = None
) -> ChatResponse:
    if not retrieved_chunks:
        lang = request.language or "en"
        domain_fallback_map = {
            "en": "I am SAARTHI, and I can help you understand NSFDC financial and educational assistance schemes. Please ask me about education loans, small businesses, self-employment, or related financial assistance.",
            "hi": "मैं सारथी हूँ, और मैं आपको NSFDC की वित्तीय और शैक्षिक सहायता योजनाओं को समझने में मदद कर सकता हूँ। कृपया मुझसे शिक्षा ऋण, छोटे व्यवसाय, स्वरोजगार या संबंधित वित्तीय सहायता के बारे में पूछें।",
            "mr": "मी सारथी आहे, आणि मी तुम्हाला NSFDC च्या आर्थिक आणि शैक्षणिक मदत योजना समजून घेण्यास मदत करू शकतो. कृपया मला शैक्षणिक कर्ज, छोटे व्यवसाय, स्वयंरोजगार किंवा संबंधित आर्थिक मदतीबद्दल विचारा.",
            "bn": "আমি সারথী, এবং আমি আপনাকে NSFDC এর আর্থিক ও শিক্ষাগত সহায়তা প্রকল্পগুলি বুঝতে সাহায্য করতে পারি। অনুগ্রহ করে আমাকে শিক্ষা ঋণ, ছোট ব্যবসা, স্ব-কর্মসংস্থান বা সম্পর্কিত আর্থিক সহায়তা সম্পর্কে জিজ্ঞাসা করুন।",
            "ta": "நான் சாரதி, மேலும் NSFDC நிதி மற்றும் கல்வி உதவித் திட்டங்களைப் புரிந்துகொள்ள நான் உங்களுக்கு உதவ முடியும். கல்வித் கடன்கள், சிறு வணிகங்கள், சுயதொழில் அல்லது தொடர்புடைய நிதி உதவி பற்றி தயவுசெய்து என்னிடம் கேளுங்கள்.",
            "te": "నేను సారథిని, మరియు NSFDC ఆర్థిక మరియు విద్యా సహాయ పథకాలను అర్థం చేసుకోవడంలో నేను మీకు సహాయపడగలను. విద్యా రుణాలు, చిన్న వ్యాపారాలు, స్వయం ఉపాధి లేదా సంబంధిత ఆర్థిక సహాయం గురించి దయచేసి నన్ను అడగండి."
        }
        answer_text = domain_fallback_map.get(lang, domain_fallback_map["en"])
        
        return ChatResponse(
            answer=answer_text,
            language=lang,
            citations=[],
            grounding_status=GroundingStatus.INSUFFICIENT_CONTEXT,
            related_scheme_ids=[],
            response_source=ResponseSource.DOMAIN_FALLBACK
        )

    eligibility_facts = None
    if request.profile:
        from app.api.mapper import PROJECT_TYPE_TO_PURPOSE, EDUCATION_STATUS_MAP
        # Map ChatProfile to UserProfile dict
        user_profile_dict = {
            "language": request.language or "en",
            "purpose": PROJECT_TYPE_TO_PURPOSE.get(request.profile.projectType) if request.profile.projectType else None,
            "family_income_inr": request.profile.annualFamilyIncome,
            "project_cost_inr": request.profile.estimatedProjectCost,
            "education_status": EDUCATION_STATUS_MAP.get(request.profile.educationStatus) if request.profile.educationStatus else None,
            "state": request.profile.stateCode,
            "district": request.profile.districtCode
        }
        
        # Strip None values
        user_profile_dict = {k: v for k, v in user_profile_dict.items() if v is not None}
        
        # Run deterministic eligibility
        eval_res = evaluate_all_schemes(user_profile_dict)
        ranked = generate_recommendations(eval_res)
        
        # Build deterministic facts for chat context
        eligibility_facts = {
            "top_recommendation": None,
            "other_eligible_schemes": []
        }
        
        if ranked.top_recommendation:
            eligibility_facts["top_recommendation"] = {
                "scheme_id": ranked.top_recommendation.scheme_id,
                "scheme_name": ranked.top_recommendation.scheme_name,
                "eligibility_status": ranked.top_recommendation.eligibility_status,
                "missing_information": ranked.top_recommendation.missing_information,
            }
        
        for alt in ranked.alternatives:
            if alt.eligibility_status in ["eligible", "potentially_eligible", "manual_verification_required"]:
                eligibility_facts["other_eligible_schemes"].append({
                    "scheme_id": alt.scheme_id,
                    "scheme_name": alt.scheme_name,
                    "eligibility_status": alt.eligibility_status
                })

    allowed_citations = _build_allowed_citations(retrieved_chunks)
    messages = _build_chat_prompt(
        query=request.query,
        chunks=retrieved_chunks,
        allowed_citations=allowed_citations,
        eligibility_facts=eligibility_facts,
        language_pref=request.language,
        chat_history=chat_history
    )
    
    model = _llm_model()

    try:
        print(f"DEBUG SARVAM KEY: '{os.environ.get('SARVAM_API_KEY')}'")
        response = litellm.completion(
            model=model,
            messages=messages,
            temperature=0.1,
            max_tokens=2048,
            extra_body={"reasoning_effort": None}
        )
        
        content = response.choices[0].message.content or ""
        content = content.strip()
        
        # Strip codeblocks
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
            
        data = json.loads(content.strip())
        
        # Parse and validate citations
        raw_citations = data.get("citations", [])
        parsed_citations = [SourceCitation(**c) for c in raw_citations]
        validated_citations = _validate_citations(parsed_citations, allowed_citations)
        
        # Enforce that related schemes are only those that were present in chunks or eligibility facts
        valid_schemes = {rc.chunk.scheme_id for rc in retrieved_chunks}
        if eligibility_facts and eligibility_facts["top_recommendation"]:
            valid_schemes.add(eligibility_facts["top_recommendation"]["scheme_id"])
        validated_related_schemes = [sid for sid in data.get("related_scheme_ids", []) if sid in valid_schemes]
        
        frontend_citations = [
            FrontendCitation(id=c.source_id, title=c.source_id, locator=c.section)
            for c in validated_citations
        ]
        
        return ChatResponse(
            answer=data["answer"],
            language=request.language or "en",
            citations=frontend_citations,
            grounding_status=GroundingStatus(data.get("grounding_status", "GROUNDED")),
            related_scheme_ids=validated_related_schemes,
            response_source=ResponseSource.RAG_LLM
        )
    except Exception as e:
        logger.error(f"LLM failure during generate_chat_answer: {e}")
        # Deterministic Fallback Logic
        lang = request.language or "en"
        fallback_prefix_map = {
            "en": "Information related to your query:\n\n",
            "hi": "आपके प्रश्न से संबंधित जानकारी:\n\n",
            "mr": "तुमच्या प्रश्नाशी संबंधित माहिती:\n\n",
            "bn": "আপনার প্রশ্ন সম্পর্কিত তথ্য:\n\n",
            "ta": "உங்கள் கேள்வி தொடர்பான தகவல்:\n\n",
            "te": "మీ ప్రశ్నకు సంబంధించిన సమాచారం:\n\n"
        }
        fallback_suffix_map = {
            "en": "\nPlease refer to the official scheme documentation for more details.",
            "hi": "\nअधिक जानकारी के लिए संबंधित योजना की आधिकारिक जानकारी देखें।",
            "mr": "\nअधिक माहितीसाठी कृपया अधिकृत योजना दस्तऐवज पहा.",
            "bn": "\nআরও বিস্তারিত জানার জন্য অনুগ্রহ করে অফিসিয়াল স্কিম ডকুমেন্টেশন দেখুন।",
            "ta": "\nமேலும் விவரங்களுக்கு அதிகாரப்பூர்வ திட்ட ஆவணத்தைப் பார்க்கவும்.",
            "te": "\nమరిన్ని వివరాల కోసం దయచేసి అధికారిక పథకం పత్రాన్ని చూడండి."
        }
        
        fallback_answer = fallback_prefix_map.get(lang, fallback_prefix_map["en"])
        
        grouped: dict[str, list[RetrievedChunk]] = {}
        for rc in retrieved_chunks:
            grouped.setdefault(rc.chunk.scheme_name, []).append(rc)
            
        for s_name, schunks in list(grouped.items())[:2]:
            fallback_answer += f"• {s_name}\n"
            
        fallback_answer += fallback_suffix_map.get(lang, fallback_suffix_map["en"])
            
        fallback_citations = []
        for c in allowed_citations[:3]:
            fallback_citations.append(FrontendCitation(id=c["source_id"], title=c["source_id"], locator=c["section"]))
            
        return ChatResponse(
            answer=fallback_answer,
            language=lang,
            citations=fallback_citations,
            grounding_status=GroundingStatus.GROUNDED,
            related_scheme_ids=list({rc.chunk.scheme_id for rc in retrieved_chunks}),
            response_source=ResponseSource.DETERMINISTIC_FALLBACK
        )
