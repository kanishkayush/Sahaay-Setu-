"""
NSFDC scheme comparison / adviser knowledge layer.

Catalogue JSON remains the scheme store. Current official FAQ facts overlay
display ranges when they conflict with historical labels. Retrieval still
ranks candidates; this module turns ranked + verified metadata into a
primary/alternative brief and a grounded adviser reply.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.eligibility_engine import load_scheme
from app.gender import FIT_MATCH, gender_fit_role, normalize_gender
from app.schemas.assistant import AssistantUICard, AssistantUICardType

_FAQ_PATH = Path(__file__).resolve().parents[2] / "data" / "rag" / "nsfdc_faq_current.json"

BUSINESS_CREDIT_IDS = ("nsfdc-mfs", "nsfdc-amy", "nsfdc-uny", "nsfdc-term-loan")
EDUCATION_CREDIT_IDS = ("nsfdc-education",)
FAQ_CREDIT_IDS = BUSINESS_CREDIT_IDS + EDUCATION_CREDIT_IDS

EXPLAIN = "EXPLAIN_SCHEME"
COMPARE = "COMPARE_SCHEMES"
OPTIONS = "OPTION_COMPARISON"
DISCOVERY = "SCHEME_DISCOVERY"

_OPTIONS_RE = re.compile(
    r"\b(other options?|other schemes?|any other|anything else|choices?|"
    r"which other|aur kya|alawa|iske alawa|ke alawa|options? hain|"
    r"kya mil sakta|aur kaunse|"
    r"all (the )?(education )?options?|education options?|show me all|"
    r"saari options?|saare options?)\b",
    re.IGNORECASE,
)
_EXPLAIN_RE = re.compile(
    r"\b(what is|explain|tell me about|kya hota|kya hai|samjhao|samjhaao|"
    r"ke baare|bare mein|bare me)\b",
    re.IGNORECASE,
)
_COMPARE_RE = re.compile(
    r"\b(vs\.?|versus|compare|comparison|ya phir|ya\s+uny|fark|difference)\b",
    re.IGNORECASE,
)


@dataclass
class SchemeFacts:
    scheme_id: str
    names: dict
    short: dict
    organization: str
    domain: str
    scheme_type: str
    assistance_type: str
    purpose: Optional[str]
    purpose_hi: Optional[str]
    project_cost_min: Optional[int]
    project_cost_min_exclusive: bool
    project_cost_max: Optional[int]
    loan_amount_min: Optional[int]
    loan_amount_max: Optional[int]
    interest_rate_pct: Optional[float]
    interest_rate_note: Optional[str]
    repayment: Optional[str]
    repayment_hi: Optional[str]
    channeling_agency: Optional[str]
    source_url: str
    verified: bool
    income_max: Optional[int] = None
    max_tenure_months: Optional[int] = None


@dataclass
class SchemeFit:
    facts: SchemeFacts
    status: str  # relevant | out_of_range | unknown
    why: str
    fit_role: str = "candidate"  # primary | related | candidate


@dataclass
class AdviserBrief:
    mode: str
    primary: Optional[SchemeFit]
    alternatives: list[SchemeFit]
    comparison: list[SchemeFit]
    missing: list[str]
    next_question: Optional[str]
    confidence: str
    answer: str
    related_ids: list[str] = field(default_factory=list)
    amount: Optional[float] = None
    income: Optional[float] = None
    activity: Optional[str] = None
    domain: Optional[str] = None
    sc_status: Optional[bool] = None
    gender: Optional[str] = None


@lru_cache(maxsize=1)
def _faq() -> dict:
    if not _FAQ_PATH.exists():
        return {"schemes": {}, "source_url": "https://nsfdc.nic.in/faqs"}
    return json.loads(_FAQ_PATH.read_text(encoding="utf-8"))


def _inr(n: Optional[int | float]) -> Optional[str]:
    if n is None:
        return None
    val = int(n)
    if val >= 100000:
        lakhs = val / 100000
        if lakhs == int(lakhs):
            return f"₹{int(lakhs)} lakh"
        return f"₹{lakhs:.2f} lakh"
    return f"₹{val:,}"


def _name(facts: SchemeFacts, lang: str) -> str:
    return facts.names.get(lang) or facts.names.get("en") or facts.scheme_id


def load_scheme_facts(scheme_id: str) -> Optional[SchemeFacts]:
    try:
        raw = load_scheme(scheme_id)
    except FileNotFoundError:
        return None
    api = raw.get("api") if isinstance(raw.get("api"), dict) else {}
    names = api.get("name") if isinstance(api.get("name"), dict) else {"en": scheme_id}
    short = api.get("shortDescription") if isinstance(api.get("shortDescription"), dict) else {}
    faq = (_faq().get("schemes") or {}).get(scheme_id) or {}
    project_min = faq.get("project_cost_min")
    project_max = faq.get("project_cost_max")
    exclusive = bool(faq.get("project_cost_min_exclusive"))
    if project_min is None and faq.get("project_cost_min_exclusive") is not None:
        project_min = faq.get("project_cost_min_exclusive")
        exclusive = True
    loan_min = api.get("minLoanAmount")
    loan_max = faq.get("loan_amount_max") if faq.get("loan_amount_max") is not None else api.get("maxLoanAmount")
    rules = api.get("eligibilityRules") if isinstance(api.get("eligibilityRules"), list) else []
    if project_max is None:
        for rule in rules:
            if rule.get("field") == "projectCost" and rule.get("operator") == "lte":
                try:
                    project_max = int(rule.get("value"))
                except (TypeError, ValueError):
                    pass
            if rule.get("field") == "projectCost" and rule.get("operator") == "between":
                vals = rule.get("value") or []
                if len(vals) == 2:
                    try:
                        project_min = project_min if project_min is not None else int(vals[0])
                        project_max = int(vals[1])
                    except (TypeError, ValueError):
                        pass
    repayment = None
    if faq.get("repayment_note"):
        repayment = faq["repayment_note"]
    elif faq.get("repayment_years"):
        repayment = f"within {faq['repayment_years']} years"
    elif faq.get("repayment_years_min") and faq.get("repayment_years_max"):
        repayment = f"up to {faq['repayment_years_min']}–{faq['repayment_years_max']} years"
    interest = faq.get("interest_rate_pct")
    if interest is None and api.get("interestRateMinPct") is not None:
        try:
            interest = float(api.get("interestRateMinPct"))
        except (TypeError, ValueError):
            interest = None
    income_max = api.get("maxAnnualFamilyIncome")
    tenure = api.get("maxTenureMonths")
    try:
        income_max_i = int(income_max) if income_max is not None else None
    except (TypeError, ValueError):
        income_max_i = None
    try:
        tenure_i = int(tenure) if tenure is not None else None
    except (TypeError, ValueError):
        tenure_i = None
    return SchemeFacts(
        scheme_id=scheme_id,
        names={str(k): str(v) for k, v in names.items()},
        short={str(k): str(v) for k, v in short.items()},
        organization=str(raw.get("organization") or "NSFDC"),
        domain=str(raw.get("domain") or ""),
        scheme_type=str(raw.get("scheme_type") or ""),
        assistance_type=str(raw.get("assistance_type") or "LOAN"),
        purpose=faq.get("purpose") or raw.get("purpose"),
        purpose_hi=faq.get("purpose_hi"),
        project_cost_min=int(project_min) if project_min is not None else None,
        project_cost_min_exclusive=exclusive,
        project_cost_max=int(project_max) if project_max is not None else None,
        loan_amount_min=int(loan_min) if loan_min is not None else None,
        loan_amount_max=int(loan_max) if loan_max is not None else None,
        interest_rate_pct=interest,
        interest_rate_note=faq.get("interest_rate_note"),
        repayment=repayment,
        repayment_hi=faq.get("repayment_hi"),
        channeling_agency=faq.get("channeling_agency"),
        source_url=str(_faq().get("source_url") or raw.get("source_url") or "https://nsfdc.nic.in/faqs"),
        verified=bool(raw.get("verified")),
        income_max=income_max_i,
        max_tenure_months=tenure_i,
    )


def catalogue_name_index() -> dict[str, str]:
    index: dict[str, str] = {}
    for sid in FAQ_CREDIT_IDS:
        facts = load_scheme_facts(sid)
        if not facts:
            continue
        slug = sid.replace("nsfdc-", "").replace("-", " ").strip()
        # Generic words like "education" must not count as a named scheme.
        if slug and slug not in {"education"}:
            index[slug] = sid
        for name in facts.names.values():
            index[name.lower()] = sid
        if sid == "nsfdc-term-loan":
            index["term loan"] = sid
            index["सावधि ऋण"] = sid
        if sid == "nsfdc-uny":
            index["udyam nidhi"] = sid
            index["uny"] = sid
        if sid == "nsfdc-mfs":
            index["micro finance"] = sid
            index["mfs"] = sid
        if sid == "nsfdc-amy":
            index["aajeevika"] = sid
            index["amy"] = sid
        if sid == "nsfdc-education":
            index["educational loan"] = sid
            index["education loan"] = sid
            index["els"] = sid
            index["शैक्षिक ऋण"] = sid
    return index


def named_scheme_ids(query: str) -> list[str]:
    q = (query or "").lower()
    found: list[str] = []
    for alias, sid in sorted(catalogue_name_index().items(), key=lambda kv: -len(kv[0])):
        if alias and alias in q and sid not in found:
            found.append(sid)
    return found


def detect_adviser_mode(query: str) -> tuple[str, list[str]]:
    named = named_scheme_ids(query)
    if _COMPARE_RE.search(query or "") or len(named) >= 2:
        return COMPARE, named
    if _OPTIONS_RE.search(query or ""):
        return OPTIONS, named
    if named and _EXPLAIN_RE.search(query or ""):
        return EXPLAIN, named
    if named and len((query or "").split()) <= 6 and not re.search(r"\b(loan|lakh|business|padhai|padai)\b", query or "", re.I):
        return EXPLAIN, named
    return DISCOVERY, named


def _in_project_range(amount: Optional[float], facts: SchemeFacts) -> str:
    if amount is None:
        return "unknown"
    if facts.project_cost_min is not None:
        if facts.project_cost_min_exclusive and amount <= facts.project_cost_min:
            return "out_of_range"
        if not facts.project_cost_min_exclusive and amount < facts.project_cost_min:
            return "out_of_range"
    if facts.project_cost_max is not None and amount > facts.project_cost_max:
        return "out_of_range"
    if facts.loan_amount_max is not None and amount > facts.loan_amount_max:
        return "out_of_range"
    return "relevant"


def _range_text(facts: SchemeFacts, lang: str) -> str:
    parts = []
    lo = facts.project_cost_min
    hi = facts.project_cost_max
    if lo is not None and hi is not None:
        if facts.project_cost_min_exclusive:
            parts.append(
                f"project cost above {_inr(lo)} and up to {_inr(hi)}"
                if lang != "hi"
                else f"परियोजना लागत {_inr(lo)} से अधिक और {_inr(hi)} तक"
            )
        else:
            parts.append(
                f"project cost {_inr(lo)}–{_inr(hi)}"
                if lang != "hi"
                else f"परियोजना लागत {_inr(lo)}–{_inr(hi)}"
            )
    elif hi is not None:
        parts.append(
            f"project cost up to {_inr(hi)}" if lang != "hi" else f"परियोजना लागत {_inr(hi)} तक"
        )
    if facts.loan_amount_max is not None:
        parts.append(
            f"maximum loan {_inr(facts.loan_amount_max)}"
            if lang != "hi"
            else f"अधिकतम ऋण {_inr(facts.loan_amount_max)}"
        )
    return "; ".join(parts)


def _why(facts: SchemeFacts, status: str, amount: Optional[float], lang: str) -> str:
    name = _name(facts, lang)
    rng = _range_text(facts, lang)
    if status == "unknown":
        if lang == "hi":
            return f"{name} NSFDC की एक संभावित option है. {rng}." if rng else f"{name} NSFDC की एक संभावित option है."
        return f"{name} may be a relevant NSFDC option. {rng}.".strip()
    if status == "relevant" and amount is not None:
        if lang == "hi":
            return f"आपकी बताई राशि {_inr(int(amount))} वर्तमान {name} सीमा के भीतर है. {rng}."
        return f"Your stated amount {_inr(int(amount))} is within the current {name} range. {rng}."
    if status == "out_of_range" and amount is not None:
        if lang == "hi":
            return f"{name} की वर्तमान सीमा ({rng}) आपकी बताई राशि {_inr(int(amount))} से मेल नहीं खाती."
        return f"{name} is outside the stated range for {_inr(int(amount))} ({rng})."
    return rng or (facts.purpose or "")


def _fit(scheme_id: str, amount: Optional[float], lang: str) -> Optional[SchemeFit]:
    facts = load_scheme_facts(scheme_id)
    if not facts or facts.assistance_type.upper() != "LOAN":
        return None
    status = _in_project_range(amount, facts)
    return SchemeFit(facts=facts, status=status, why=_why(facts, status, amount, lang))


def _purpose_fit_code(domain: Optional[str], facts_domain: Optional[str]) -> str:
    wanted = (domain or "").upper()
    have = (facts_domain or "").upper()
    if not wanted or wanted in {"OTHER", "UNKNOWN"}:
        return "UNKNOWN"
    if have and have == wanted:
        return "MATCH"
    if wanted == "BUSINESS" and have in {"BUSINESS", "MICRO_ENTERPRISE", "SELF_EMPLOYMENT"}:
        return "MATCH"
    if wanted in {"BUSINESS", "EDUCATION", "AGRICULTURE"} and have and have != wanted:
        return "MISMATCH"
    return "UNKNOWN"


def _verification_status(facts: SchemeFacts) -> str:
    if facts.scheme_id in FAQ_CREDIT_IDS and facts.verified:
        return "VERIFIED"
    if facts.verified:
        return "PARTIAL"
    return "UNVERIFIED"


def _income_fit_code(income: Optional[float], income_max: Optional[int]) -> str:
    if income is None or income_max is None:
        return "UNKNOWN"
    return "WITHIN_LIMIT" if income <= income_max else "ABOVE_LIMIT"


def _amount_fit_code(status: str, assistance_type: str) -> str:
    if (assistance_type or "").upper() != "LOAN":
        return "NOT_A_LOAN"
    if status == "relevant":
        return "WITHIN_RANGE"
    if status == "out_of_range":
        return "OUTSIDE_RANGE"
    return "UNKNOWN"


def _reason(kind: str, en: str, hi: str, lang: str) -> dict:
    return {"kind": kind, "text": hi if lang == "hi" else en}


def structured_why_selected(
    *,
    facts: SchemeFacts,
    status: str,
    lang: str,
    amount: Optional[float] = None,
    income: Optional[float] = None,
    activity: Optional[str] = None,
    domain: Optional[str] = None,
    sc_status: Optional[bool] = None,
    course_fit: Optional[str] = None,
    related_agriculture: bool = False,
    gender: Optional[str] = None,
    gender_fit: Optional[str] = None,
) -> list[dict]:
    """Deterministic fit reasons. UNKNOWN stays UNKNOWN — never coerced to MATCH."""
    hi = lang == "hi"
    reasons: list[dict] = []
    if gender_fit == "MATCH":
        reasons.append(_reason(
            "MATCH",
            "The catalogue record is specifically for women beneficiaries.",
            "कैटलॉग रिकॉर्ड विशेष रूप से महिला लाभार्थियों के लिए है।",
            lang,
        ))
    elif gender_fit == "MISMATCH":
        reasons.append(_reason(
            "MISMATCH",
            "The catalogue record does not match the stated gender.",
            "कैटलॉग रिकॉर्ड बताए गए लिंग से मेल नहीं खाता।",
            lang,
        ))
    elif gender:
        reasons.append(_reason(
            "INFO",
            "Gender restriction is not published for this scheme.",
            "इस योजना के लिए लिंग संबंधी पाबंदी प्रकाशित नहीं है।",
            lang,
        ))
    income_fit = _income_fit_code(income, facts.income_max)
    if income_fit == "WITHIN_LIMIT" and facts.income_max is not None:
        reasons.append(_reason(
            "MATCH",
            f"Your family income is within the published ceiling of {_inr(facts.income_max)}.",
            f"आपकी पारिवारिक आय {_inr(facts.income_max)} की प्रकाशित सीमा के भीतर है।",
            lang,
        ))
    elif income_fit == "ABOVE_LIMIT" and facts.income_max is not None:
        reasons.append(_reason(
            "MISMATCH",
            f"Your family income is above the published ceiling of {_inr(facts.income_max)}.",
            f"आपकी पारिवारिक आय {_inr(facts.income_max)} की प्रकाशित सीमा से अधिक है।",
            lang,
        ))
    elif income is None:
        reasons.append(_reason(
            "INFO",
            "Family income confirmation is required.",
            "पारिवारिक आय की पुष्टि आवश्यक है।",
            lang,
        ))

    amount_fit = _amount_fit_code(status, facts.assistance_type)
    if amount_fit == "WITHIN_RANGE" and amount is not None:
        reasons.append(_reason(
            "MATCH",
            f"Your stated amount {_inr(int(amount))} is within the scheme limit.",
            f"आपकी परियोजना लागत योजना की सीमा में है ({_inr(int(amount))})।",
            lang,
        ))
    elif amount_fit == "OUTSIDE_RANGE" and amount is not None:
        reasons.append(_reason(
            "MISMATCH",
            f"Your stated amount {_inr(int(amount))} is outside the scheme limit.",
            f"आपकी परियोजना लागत योजना की सीमा से बाहर है ({_inr(int(amount))})।",
            lang,
        ))
    elif amount is None:
        reasons.append(_reason(
            "INFO",
            "Project or loan amount confirmation is required.",
            "परियोजना/ऋण राशि की पुष्टि आवश्यक है।",
            lang,
        ))

    vague = {"", "BUSINESS", "GENERAL_BUSINESS", "GENERAL", "FARMING", "AGRICULTURE", "EDUCATION_LOAN", "EDUCATION"}
    act = str(activity or "").upper()
    domain_u = (domain or "").upper()
    if related_agriculture:
        reasons.append(_reason(
            "INFO",
            "The scheme record lists agriculture and allied work among many income-generating activities. It is not a dedicated crop-farming product.",
            "योजना विवरण में कृषि व संबद्ध गतिविधियाँ कई आय-सृजन कामों में शामिल हैं। यह समर्पित फसल ऋण नहीं है।",
            lang,
        ))
    elif domain_u == "EDUCATION" and (facts.domain or "").upper() == "EDUCATION":
        if course_fit == "MATCH" and act and act not in vague:
            reasons.append(_reason(
                "MATCH",
                f"Your course ({act.replace('_', ' ').title()}) matches this education product.",
                f"आपका कोर्स ({act.replace('_', ' ')}) इस शिक्षा योजना से मेल खाता है।",
                lang,
            ))
        elif act in vague or not act:
            reasons.append(_reason(
                "INFO",
                "Course confirmation is required.",
                "कोर्स की पुष्टि आवश्यक है।",
                lang,
            ))
        else:
            reasons.append(_reason(
                "INFO",
                "Course fit could not be confirmed from the scheme record.",
                "कोर्स मेल की पुष्टि योजना रिकॉर्ड से नहीं हो सकी।",
                lang,
            ))
    elif act and act not in vague and not related_agriculture:
        purpose = (facts.purpose or "") + " " + " ".join(facts.short.values())
        blob = purpose.lower()
        token = act.replace("_", " ").lower()
        if token in blob or any(part in blob for part in token.split() if len(part) > 3):
            reasons.append(_reason(
                "MATCH",
                f"Your activity ({token}) matches the scheme objectives in the record.",
                f"आपकी गतिविधि योजना के उद्देश्यों से मेल खाती है।",
                lang,
            ))
        else:
            reasons.append(_reason(
                "INFO",
                f"Activity ({token}) fit needs confirmation against the scheme record.",
                "गतिविधि के मेल की पुष्टि आवश्यक है।",
                lang,
            ))
    elif domain_u == "BUSINESS" and (facts.domain or "").upper() == "BUSINESS":
        reasons.append(_reason(
            "INFO",
            "This is an NSFDC income-generating credit product. Confirm the exact activity with a channel partner.",
            "यह NSFDC की आय-सृजन ऋण योजना है। सटीक गतिविधि की पुष्टि चैनल पार्टनर से करें।",
            lang,
        ))

    if sc_status is True:
        reasons.append(_reason(
            "MATCH",
            "Scheduled Caste status is recorded in your profile.",
            "आपकी प्रोफ़ाइल में अनुसूचित जाति की जानकारी दर्ज है।",
            lang,
        ))
    elif sc_status is False:
        reasons.append(_reason(
            "INFO",
            "NSFDC credit is for Scheduled Caste applicants — confirmation is required.",
            "NSFDC ऋण अनुसूचित जाति के आवेदकों के लिए है — पुष्टि आवश्यक है।",
            lang,
        ))
    else:
        reasons.append(_reason(
            "INFO",
            "SC/ST certificate confirmation is required.",
            "SC/ST प्रमाण-पत्र की पुष्टि आवश्यक है।",
            lang,
        ))

    verify = _verification_status(facts)
    if verify != "VERIFIED":
        reasons.append(_reason(
            "INFO",
            "Verification required. Current details could not be confirmed.",
            "सत्यापन आवश्यक है। वर्तमान विवरण की पुष्टि नहीं हो सकी।",
            lang,
        ))
    return reasons


def make_scheme_card(
    *,
    fit: SchemeFit,
    lang: str,
    is_primary: bool,
    amount: Optional[float] = None,
    income: Optional[float] = None,
    activity: Optional[str] = None,
    domain: Optional[str] = None,
    sc_status: Optional[bool] = None,
    course_fit: Optional[str] = None,
    eligibility_notes: Optional[str] = None,
    gender: Optional[str] = None,
    gender_fit: Optional[str] = None,
    purpose_fit: Optional[str] = None,
) -> AssistantUICard:
    facts = fit.facts
    related = fit.fit_role == "related"
    verify = _verification_status(facts)
    why = structured_why_selected(
        facts=facts,
        status=fit.status,
        lang=lang,
        amount=amount,
        income=income,
        activity=activity,
        domain=domain,
        sc_status=sc_status,
        course_fit=course_fit,
        related_agriculture=related and (domain or "").upper() == "AGRICULTURE",
        gender=gender,
        gender_fit=gender_fit,
    )
    if related:
        fit_status = "RELATED"
    elif is_primary:
        fit_status = "MATCH"
    elif fit.status == "relevant":
        fit_status = "MATCH"
    else:
        fit_status = "UNKNOWN"
    caption = (
        "आपकी जानकारी के आधार पर मेल खाता विकल्प"
        if lang == "hi" and not related
        else (
            "Matches your details"
            if not related
            else (
                "Related general NSFDC credit — not a dedicated crop scheme"
                if lang != "hi"
                else "संबंधित सामान्य NSFDC ऋण — समर्पित फसल योजना नहीं"
            )
        )
    )
    if related:
        caption = (
            "संबंधित विकल्प — फसल ऋण होने का दावा नहीं"
            if lang == "hi"
            else "Related option — not claimed as a crop loan"
        )
    elif is_primary:
        caption = (
            "दी गई जानकारी के आधार पर सबसे संबंधित"
            if lang == "hi"
            else "Most relevant based on the information provided"
        )
    verified_financials = verify == "VERIFIED"
    return AssistantUICard(
        type=AssistantUICardType.SCHEME_CARD,
        schemeId=facts.scheme_id,
        schemeName=_name(facts, lang),
        reason=caption,
        eligible=None,
        organization=facts.organization,
        domain=facts.domain or domain,
        assistanceType=facts.assistance_type,
        verificationStatus=verify,
        fitStatus=fit_status,
        fitReasons=why,
        whySelected=why,
        amountFit=_amount_fit_code(fit.status, facts.assistance_type),
        incomeFit=_income_fit_code(income, facts.income_max),
        courseFit=course_fit,
        genderFit=gender_fit,
        purposeFit=purpose_fit,
        eligibilityNotes=eligibility_notes,
        maxLoanAmount=float(facts.loan_amount_max) if verified_financials and facts.loan_amount_max is not None else None,
        interestRatePct=float(facts.interest_rate_pct) if verified_financials and facts.interest_rate_pct is not None else None,
        maxTenureMonths=facts.max_tenure_months if verified_financials else None,
        isPrimary=bool(is_primary and not related),
        action="VIEW_DETAILS",
    )


def _agriculture_incidental(scheme: dict) -> bool:
    from app.recommendation_engine import agriculture_fit_role
    return agriculture_fit_role(scheme) == "related"


def _build_agriculture_brief(
    *,
    amount: Optional[float],
    activity: Optional[str],
    lang: str,
    income: Optional[float],
    query: Optional[str],
    sc_status: Optional[bool],
    mode: str,
    gender: Optional[str] = None,
) -> AdviserBrief:
    hi = lang == "hi"
    related_fits: list[SchemeFit] = []
    dedicated_fits: list[SchemeFit] = []
    from app.recommendation_engine import agriculture_fit_role
    from app.rag.scheme_knowledge import iter_schemes

    seen: set[str] = set()
    for raw in iter_schemes():
        sid = str(raw.get("scheme_id") or "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        role = agriculture_fit_role(raw, activity, "AGRICULTURE")
        if role == "none":
            continue
        fit = _fit(sid, amount, lang)
        if not fit:
            continue
        if role == "related":
            fit.fit_role = "related"
            related_fits.append(fit)
        else:
            dedicated_fits.append(fit)

    primary = dedicated_fits[0] if dedicated_fits else None
    alts = [f for f in (related_fits if not primary else dedicated_fits[1:] + related_fits)][:4]
    cropish = str(activity or "").upper() in {
        "CROP_FARMING", "RICE_FARMING", "WHEAT_FARMING", "VEGETABLE_FARMING",
        "HORTICULTURE", "FASAL",
    } or any(
        tok in (query or "").lower()
        for tok in ("फसल", "fasal", "crop", "rice", "chawal", "paddy", "धान", "चावल")
    )
    if primary is None:
        if cropish:
            answer = (
                "आपकी फसल खेती के लिए मुझे वर्तमान सत्यापित NSFDC catalogue में स्पष्ट रूप से मेल खाने वाली योजना नहीं मिली। "
                "मैं उपलब्ध विकल्पों और verification-required schemes भी दिखा सकता हूँ। "
                "सावधि ऋण एक सामान्य आय-सृजन ऋण है जिसमें कृषि व संबद्ध गतिविधियाँ कई कामों के साथ लिखी हैं — यह समर्पित फसल ऋण नहीं है।"
                if hi else
                "I could not find a clearly matching crop-farming scheme in the current verified NSFDC catalogue. "
                "I can still show related options and schemes that require verification. "
                "Term Loan is general NSFDC term finance that lists agriculture and allied activities among many income-generating uses — it is not a dedicated crop loan."
            )
        else:
            answer = (
                "कृषि/खेती के लिए वर्तमान सत्यापित NSFDC catalogue में मुझे कोई समर्पित कृषि ऋण योजना नहीं मिली। "
                "कुछ सामान्य NSFDC ऋण योजनाओं के विवरण में कृषि व संबद्ध गतिविधियाँ अन्य आय-सृजन कामों के साथ लिखी हैं। "
                "मैं उन्हें संबंधित विकल्प के रूप में दिखा सकता हूँ — यह फसल ऋण होने का दावा नहीं है।"
                if hi else
                "The current verified NSFDC catalogue does not contain a dedicated agriculture or crop-farming loan. "
                "Some general NSFDC credit products mention agriculture and allied activities among other income-generating uses. "
                "I can show those as related options — not as a dedicated crop loan."
            )
        if amount is None:
            answer += (
                " अगर आप अनुमानित राशि बताएँ, तो मैं सीमा के हिसाब से विकल्प छांट सकता हूँ।"
                if hi else
                " If you share an approximate amount, I can narrow the related options."
            )
        confidence = "low"
    else:
        answer = (
            f"आपकी जानकारी के आधार पर {_name(primary.facts, lang)} संबंधित लगता है। मैंने नीचे इसकी जानकारी दी है।"
            if hi else
            f"Based on the information provided, {_name(primary.facts, lang)} appears relevant. Details are below."
        )
        confidence = "medium"
    related_ids = []
    if primary:
        related_ids.append(primary.facts.scheme_id)
    related_ids.extend(f.facts.scheme_id for f in alts if f.facts.scheme_id not in related_ids)
    return AdviserBrief(
        mode=mode,
        primary=primary,
        alternatives=alts,
        comparison=([primary] if primary else []) + alts,
        missing=[] if amount is not None else ["project_cost"],
        next_question=None if amount is not None else (
            "आपकी परियोजना की अनुमानित लागत लगभग कितनी है?" if hi else "Approximately how much will your project cost?"
        ),
        confidence=confidence,
        answer=answer,
        related_ids=related_ids,
        amount=amount,
        income=income,
        activity=activity,
        domain="AGRICULTURE",
        sc_status=sc_status,
        gender=gender,
    )


def _build_women_brief(
    *,
    gender: Optional[str],
    amount: Optional[float],
    lang: str,
    income: Optional[float],
    query: Optional[str],
    sc_status: Optional[bool],
    mode: str,
    activity: Optional[str] = None,
) -> AdviserBrief:
    """Discover schemes from catalogue gender metadata. Do not invent a purpose."""
    hi = lang == "hi"
    from app.rag.scheme_knowledge import iter_schemes

    matches: list[SchemeFit] = []
    seen: set[str] = set()
    for raw in iter_schemes():
        sid = str(raw.get("scheme_id") or "")
        if not sid or sid in seen:
            continue
        seen.add(sid)
        if gender_fit_role(raw, gender) != FIT_MATCH:
            continue
        facts = load_scheme_facts(sid)
        if facts is None:
            continue
        status = _in_project_range(amount, facts)
        if status == "out_of_range":
            status = "unknown"
        fit = SchemeFit(
            facts=facts,
            status=status,
            why=_why(facts, status, amount, lang),
            fit_role="primary",
        )
        matches.append(fit)

    primary = matches[0] if matches else None
    alts = matches[1:4]
    if primary is None:
        answer = (
            "मुझे उपलब्ध सत्यापित जानकारी में महिलाओं के लिए विशेष रूप से मेल खाने वाली योजना नहीं मिली। "
            "मैं सामान्य योजनाएं भी दिखा सकता हूँ।"
            if hi else
            "I could not find a scheme that specifically matches women beneficiaries in the available verified information. "
            "I can also show general schemes."
        )
        confidence = "low"
    else:
        verify = _verification_status(primary.facts)
        name = _name(primary.facts, lang)
        if verify == "VERIFIED":
            answer = (
                f"कैटलॉग में महिला लाभार्थियों के लिए {_name(primary.facts, lang)} विशेष रूप से दर्ज है। विवरण नीचे हैं।"
                if hi else
                f"The catalogue records {_name(primary.facts, lang)} specifically for women beneficiaries. Details are below."
            )
        else:
            answer = (
                f"कैटलॉग में महिला लाभार्थियों के लिए {name} विशेष रूप से दर्ज है। "
                "वर्तमान विवरण की पूरी पुष्टि नहीं हो सकी है। विवरण नीचे हैं।"
                if hi else
                f"The catalogue records {name} specifically for women beneficiaries. "
                "Current details could not be fully confirmed. Details are below."
            )
        confidence = "medium" if verify == "VERIFIED" else "low"
    related_ids = [f.facts.scheme_id for f in matches]
    return AdviserBrief(
        mode=mode,
        primary=primary,
        alternatives=alts,
        comparison=([primary] if primary else []) + alts,
        missing=[],
        next_question=None,
        confidence=confidence,
        answer=answer,
        related_ids=related_ids,
        amount=amount,
        income=income,
        activity=activity,
        domain=None,
        sc_status=sc_status,
        gender=gender,
    )


def _universe(domain: Optional[str]) -> tuple[str, ...]:
    if (domain or "").upper() == "EDUCATION":
        return EDUCATION_CREDIT_IDS
    if (domain or "").upper() == "AGRICULTURE":
        return ()
    return BUSINESS_CREDIT_IDS


def build_brief(
    *,
    domain: Optional[str],
    amount: Optional[float],
    activity: Optional[str],
    lang: str,
    mode: str = DISCOVERY,
    named_ids: Optional[list[str]] = None,
    retrieved_ids: Optional[list[str]] = None,
    income: Optional[float] = None,
    query: Optional[str] = None,
    sc_status: Optional[bool] = None,
    gender: Optional[str] = None,
) -> AdviserBrief:
    lang = "hi" if lang == "hi" else "en"
    named_ids = named_ids or []
    retrieved_ids = retrieved_ids or []
    gender = normalize_gender(gender)
    domain_key = (domain or "").upper()
    if gender and domain_key not in {"AGRICULTURE", "EDUCATION", "BUSINESS"} and mode != EXPLAIN:
        return _build_women_brief(
            gender=gender,
            amount=amount,
            lang=lang,
            income=income,
            query=query,
            sc_status=sc_status,
            mode=mode,
            activity=activity,
        )
    if domain_key == "AGRICULTURE" and mode != EXPLAIN:
        return _build_agriculture_brief(
            amount=amount,
            activity=activity,
            lang=lang,
            income=income,
            query=query,
            sc_status=sc_status,
            mode=mode,
            gender=gender,
        )
    if (domain or "").upper() == "EDUCATION" and mode != EXPLAIN:
        from app.rag.education_advisor import (
            build_education_brief,
            education_ui_cards,
        )

        edu = build_education_brief(
            amount=amount,
            income=income,
            course=activity,
            lang=lang,
            query=query,
            activity=activity,
        )
        def _as_fit(opt):
            facts = load_scheme_facts(opt.scheme_id)
            if facts is None:
                facts = SchemeFacts(
                    scheme_id=opt.scheme_id,
                    names={"en": opt.scheme_name, "hi": opt.scheme_name},
                    short={},
                    organization=opt.organization,
                    domain="EDUCATION",
                    scheme_type=opt.assistance_type,
                    assistance_type=opt.assistance_type,
                    purpose=opt.purpose or None,
                    purpose_hi=None,
                    project_cost_min=None,
                    project_cost_min_exclusive=False,
                    project_cost_max=None,
                    loan_amount_min=None,
                    loan_amount_max=opt.loan_amount_max,
                    interest_rate_pct=None,
                    interest_rate_note=None,
                    repayment=None,
                    repayment_hi=None,
                    channeling_agency=None,
                    source_url=opt.source_url or ("https://nsfdc.nic.in/faqs" if opt.organization == "NSFDC" else ""),
                    verified=opt.verification_status == "VERIFIED",
                )
            status = "relevant" if opt.relevance == "HIGH" else ("unknown" if opt.requires_verification else "relevant")
            return SchemeFit(facts=facts, status=status, why=opt.why_relevant)
        loans = [_as_fit(o) for o in edu.primary_loan_options]
        support = [_as_fit(o) for o in edu.other_education_support]
        primary = next((f for f in loans if f.facts.scheme_id == "nsfdc-education"), loans[0] if loans else None)
        alts = [f for f in loans + support if not primary or f.facts.scheme_id != primary.facts.scheme_id]
        brief = AdviserBrief(
            mode=mode,
            primary=primary,
            alternatives=alts,
            comparison=([primary] if primary else []) + alts,
            missing=edu.missing,
            next_question=edu.next_question,
            confidence="medium" if primary else "low",
            answer=edu.answer,
            related_ids=edu.related_ids,
            amount=amount,
            income=income,
            activity=activity,
            domain="EDUCATION",
            sc_status=sc_status,
            gender=gender,
        )
        brief._education_cards = education_ui_cards(edu, lang, gender=gender)  # type: ignore[attr-defined]
        return brief
    universe = list(_universe(domain))
    if mode == EXPLAIN and named_ids:
        universe = named_ids[:1]
    elif mode == COMPARE and named_ids:
        universe = named_ids[:4]
    fits = [f for sid in universe if (f := _fit(sid, amount, lang))]
    relevant = [f for f in fits if f.status == "relevant"]
    unknown = [f for f in fits if f.status == "unknown"]
    out = [f for f in fits if f.status == "out_of_range"]
    if amount is None:
        pool = unknown or relevant
        if (domain or "").upper() == "EDUCATION" and pool:
            primary = pool[0]
            alts = pool[1:]
        else:
            primary = None
            alts = pool
        missing = ["project_cost"] if (domain or "").upper() != "EDUCATION" else []
        confidence = "low"
    else:
        pool = relevant
        if retrieved_ids:
            pool = sorted(
                pool,
                key=lambda f: (0 if f.facts.scheme_id in retrieved_ids else 1, universe.index(f.facts.scheme_id) if f.facts.scheme_id in universe else 99),
            )
        primary = pool[0] if pool else None
        alts = [f for f in pool[1:4]]
        missing = []
        if not activity or str(activity).upper() in {"BUSINESS", "GENERAL_BUSINESS", "GENERAL", "FARMING", "AGRICULTURE"}:
            if (domain or "").upper() != "EDUCATION":
                missing.append("activity")
        confidence = "medium" if primary else "low"
    if mode == OPTIONS:
        primary = None
        pool = unknown or relevant or fits
        if named_ids:
            others = [f for f in pool if f.facts.scheme_id not in named_ids]
            alts = (others or pool)[:4]
        else:
            alts = pool[:4]
        confidence = "medium" if amount is not None else "low"
    if mode == EXPLAIN and named_ids:
        primary = _fit(named_ids[0], amount, lang)
        alts = [_fit(sid, amount, lang) for sid in _universe(domain) if sid != named_ids[0]]
        alts = [a for a in alts if a][:3]
        missing = []
        confidence = "high" if primary else "low"
    if mode == COMPARE and named_ids:
        comparison = [f for sid in named_ids if (f := _fit(sid, amount, lang))]
        primary = comparison[0] if comparison else None
        alts = comparison[1:]
        fits = comparison
        missing = []
        confidence = "high"
    else:
        comparison = ( ([primary] if primary else []) + alts )[:4]

    next_q = _next_question(domain, amount, activity, lang, missing)
    answer = render_answer(
        mode=mode,
        domain=domain,
        amount=amount,
        activity=activity,
        lang=lang,
        primary=primary,
        alternatives=alts if mode != EXPLAIN else [a for a in alts if a.status != "out_of_range"][:3] or alts[:3],
        out_of_range=out,
        next_question=next_q,
    )
    if mode == OPTIONS and named_ids:
        named_names = []
        for sid in named_ids:
            facts = load_scheme_facts(sid)
            if facts:
                named_names.append(_name(facts, lang))
        if named_names:
            prefix = (
                f"{', '.join(named_names)} के अलावा NSFDC के कुछ और options हैं. "
                if lang == "hi"
                else f"Besides {', '.join(named_names)}, NSFDC has other credit options. "
            )
            answer = prefix + answer
    related = []
    if primary:
        related.append(primary.facts.scheme_id)
    related.extend(f.facts.scheme_id for f in alts if f.facts.scheme_id not in related)
    return AdviserBrief(
        mode=mode,
        primary=primary,
        alternatives=alts,
        comparison=comparison,
        missing=missing,
        next_question=next_q,
        confidence=confidence,
        answer=answer,
        related_ids=related,
        amount=amount,
        income=income,
        activity=activity,
        domain=domain,
        sc_status=sc_status,
        gender=gender,
    )


def _next_question(
    domain: Optional[str],
    amount: Optional[float],
    activity: Optional[str],
    lang: str,
    missing: list[str],
) -> Optional[str]:
    if (domain or "").upper() == "EDUCATION":
        return None
    if "project_cost" in missing or amount is None:
        return (
            "आपकी परियोजना की अनुमानित लागत लगभग कितनी है?"
            if lang == "hi"
            else "Approximately how much will your project cost?"
        )
    if "activity" in missing:
        return (
            "आप कौन-सा व्यवसाय या गतिविधि शुरू करना चाहते हैं?"
            if lang == "hi"
            else "What business or activity are you planning?"
        )
    return (
        "क्या आप दस्तावेज़ या नज़दीकी चैनल पार्टनर के बारे में जानना चाहते हैं?"
        if lang == "hi"
        else "Would you like documents or a nearby channel partner next?"
    )


def _scheme_blurb(fit: SchemeFit, lang: str) -> str:
    facts = fit.facts
    name = _name(facts, lang)
    what = (
        facts.purpose_hi
        if lang == "hi" and facts.purpose_hi
        else facts.purpose
    ) or (facts.short.get(lang) or facts.short.get("en") or "")
    rng = _range_text(facts, lang)
    rate = None
    note_hi = None
    if facts.interest_rate_pct is not None:
        rate = f"{facts.interest_rate_pct:g}% p.a." if lang != "hi" else f"{facts.interest_rate_pct:g}% प्रति वर्ष"
    elif facts.interest_rate_note:
        note_hi = ((_faq().get("schemes") or {}).get(facts.scheme_id) or {}).get("interest_rate_note_hi")
        rate = note_hi if lang == "hi" and note_hi else facts.interest_rate_note
    bits = [what, rng]
    if rate:
        bits.append(rate if lang != "hi" or note_hi else f"लाभार्थी ब्याज {rate}")
    repay = facts.repayment_hi if lang == "hi" and facts.repayment_hi else facts.repayment
    if repay:
        bits.append(repay if lang != "hi" or facts.repayment_hi else f"चुकौती {repay}")
    body = ". ".join(b.rstrip(".") for b in bits if b)
    return f"{name}: {body}." if body else f"{name}."


def render_answer(
    *,
    mode: str,
    domain: Optional[str],
    amount: Optional[float],
    activity: Optional[str],
    lang: str,
    primary: Optional[SchemeFit],
    alternatives: list[SchemeFit],
    out_of_range: list[SchemeFit],
    next_question: Optional[str],
) -> str:
    hi = lang == "hi"
    lines: list[str] = []
    if mode == EXPLAIN and primary:
        lines.append(_scheme_blurb(primary, lang))
        if alternatives:
            names = ", ".join(_name(a.facts, lang) for a in alternatives[:3])
            lines.append(
                f"NSFDC की अन्य संभावित credit options: {names}."
                if hi
                else f"Other NSFDC credit options that may be relevant: {names}."
            )
    elif mode == COMPARE:
        lines.append(
            "वर्तमान आधिकारिक NSFDC जानकारी के आधार पर तुलना:"
            if hi
            else "Comparison based on current official NSFDC information:"
        )
        for fit in ([primary] if primary else []) + alternatives:
            lines.append(_scheme_blurb(fit, lang) + " " + fit.why)
    elif mode == OPTIONS:
        names = ", ".join(_name(a.facts, lang) for a in alternatives[:4])
        lines.append(
            f"NSFDC के कुछ संभावित options हैं, जैसे {names}. कौन-सा option आपके लिए relevant हो सकता है, यह मुख्यतः परियोजना लागत और गतिविधि पर निर्भर करता है."
            if hi
            else f"Based on what you've told me, NSFDC credit products such as {names} may be relevant. I am not declaring eligibility — the right option depends mainly on project cost and the type of activity."
        )
    else:
        if (domain or "").upper() == "EDUCATION" and primary:
            lines.append(
                f"पढ़ाई के loan के लिए NSFDC की {_name(primary.facts, lang)} relevant है."
                if hi
                else f"For an education loan, NSFDC's {_name(primary.facts, lang)} is the relevant credit product."
            )
            lines.append(_scheme_blurb(primary, lang))
        elif amount is None:
            names = ", ".join(_name(a.facts, lang) for a in alternatives[:4])
            lines.append(
                f"व्यवसाय/स्वरोजगार के लिए NSFDC के कई credit options हैं, जैसे {names}. कौन-सा option आपके लिए relevant हो सकता है, यह मुख्यतः परियोजना लागत और गतिविधि पर निर्भर करता है."
                if hi
                else f"NSFDC has several credit options for income-generating activity, including {names}. Which one may fit depends mainly on project cost and the type of activity."
            )
        else:
            if primary:
                lines.append(
                    "आपकी जानकारी के आधार पर एक संबंधित विकल्प मिला है। मैंने नीचे इसकी जानकारी दी है।"
                    if hi
                    else "A relevant option based on your details is below."
                )
                lines.append(
                    f"आपकी बताई राशि {_inr(int(amount))} के आधार पर {_name(primary.facts, lang)} मेल खाता NSFDC विकल्प है।"
                    if hi
                    else f"Based on the amount you mentioned ({_inr(int(amount))}), {_name(primary.facts, lang)} matches your details."
                )
                lines.append(_scheme_blurb(primary, lang))
                lines.append(primary.why)
            relevant_alts = [a for a in alternatives if a.status == "relevant"]
            if relevant_alts:
                names = ", ".join(_name(a.facts, lang) for a in relevant_alts)
                lines.append(
                    f"इसी सीमा में अन्य संभावित option: {names}."
                    if hi
                    else f"Other options that may also fit this range: {names}."
                )
            why_not = [a for a in out_of_range[:2]]
            for fit in why_not:
                lines.append(fit.why)
        if activity and str(activity).upper() not in {
            "BUSINESS", "GENERAL_BUSINESS", "GENERAL", "EDUCATION_LOAN", "FARMING", "AGRICULTURE",
        }:
            act = str(activity).replace("_", " ").lower()
            lines.append(
                f"मैंने आपकी गतिविधि ({act}) भी ध्यान में रखी है."
                if hi
                else f"I have also noted your activity ({act})."
            )
    if next_question:
        lines.append(next_question)
    return " ".join(l.strip() for l in lines if l and l.strip())


def ui_cards(brief: AdviserBrief, lang: str) -> list[AssistantUICard]:
    extra = getattr(brief, "_education_cards", None)
    if extra:
        return list(extra)
    cards: list[AssistantUICard] = []
    seen: set[str] = set()
    ordered: list[SchemeFit] = []
    if brief.primary:
        ordered.append(brief.primary)
    ordered.extend(brief.alternatives)
    primary_id = brief.primary.facts.scheme_id if brief.primary else None
    for fit in ordered[:6]:
        if fit.status == "out_of_range":
            continue
        sid = fit.facts.scheme_id
        if sid in seen:
            continue
        seen.add(sid)
        cards.append(
            make_scheme_card(
                fit=fit,
                lang=lang,
                is_primary=bool(primary_id and sid == primary_id and fit.fit_role != "related"),
                amount=brief.amount,
                income=brief.income,
                activity=brief.activity,
                domain=brief.domain,
                sc_status=brief.sc_status,
                gender=brief.gender,
                gender_fit=_card_gender_fit(fit, brief.gender),
                purpose_fit=(
                    "RELATED"
                    if fit.fit_role == "related"
                    else _purpose_fit_code(brief.domain, fit.facts.domain)
                ),
            )
        )
    return cards


def _card_gender_fit(fit: SchemeFit, gender: Optional[str]) -> Optional[str]:
    if not gender:
        return None
    try:
        raw = load_scheme(fit.facts.scheme_id)
    except Exception:
        return "UNKNOWN"
    return gender_fit_role(raw, gender)
