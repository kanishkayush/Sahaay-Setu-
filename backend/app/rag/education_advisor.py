"""
Education-catalogue adviser.

Discovers education-related schemes from catalogue metadata (domain /
officialCategory), classifies assistance type, and compares them against
the user's requested amount, family income, and course — without treating
unverified records as confirmed eligibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from typing import Optional

from app.rag.scheme_knowledge import audit_scheme, iter_schemes
from app.gender import gender_fit_role
from app.schemas.assistant import AssistantUICard, AssistantUICardType

NSFDC_LOAN_INCOME_CEILING = 500_000  # Current NSFDC FAQ, effective 7 Jan 2026
NSFDC_ELS_LOAN_MAX = 4_000_000
SOURCE_FAQ = "https://nsfdc.nic.in/faqs"

ASSISTANCE_LOAN = "LOAN"
ASSISTANCE_SCHOLARSHIP = "SCHOLARSHIP"
ASSISTANCE_SUBSIDY = "INTEREST_SUBSIDY"
ASSISTANCE_FELLOWSHIP = "FELLOWSHIP"
ASSISTANCE_COACHING = "COACHING"
ASSISTANCE_OTHER = "OTHER_FINANCIAL_ASSISTANCE"

VERIFIED = "VERIFIED"
PARTIAL = "PARTIAL"
UNVERIFIED = "UNVERIFIED"

WITHIN_RANGE = "WITHIN_RANGE"
OUTSIDE_RANGE = "OUTSIDE_RANGE"
AMOUNT_UNKNOWN = "UNKNOWN"
NOT_A_LOAN = "NOT_A_LOAN"

WITHIN_LIMIT = "WITHIN_LIMIT"
ABOVE_LIMIT = "ABOVE_LIMIT"
INCOME_UNKNOWN = "UNKNOWN"

COURSE_MATCH = "MATCH"
COURSE_UNKNOWN = "UNKNOWN"

_TECHNICAL_COURSE = {
    "BTECH", "B.TECH", "ENGINEERING", "ENGINEERING_GENERAL", "MTECH",
    "MBBS", "MEDICAL", "NURSING", "ITI", "DIPLOMA", "MCA", "MBA",
    "BCA", "BBA", "LLB", "VOCATIONAL", "PROFESSIONAL", "TECHNICAL",
}


@dataclass
class EducationOption:
    scheme_id: str
    scheme_name: str
    organization: str
    assistance_type: str
    verification_status: str
    metadata_quality: str
    source_url: str
    loan_amount_max: Optional[int]
    income_limit: Optional[int]
    amount_fit: str
    income_fit: str
    course_fit: str
    why_relevant: str
    why_not: str
    requires_verification: bool
    relevance: str  # HIGH | MEDIUM | LOW
    purpose: str = ""


@dataclass
class EducationBrief:
    options: list[EducationOption]
    primary_loan_options: list[EducationOption]
    other_education_support: list[EducationOption]
    missing: list[str]
    next_question: Optional[str]
    answer: str
    related_ids: list[str] = field(default_factory=list)


def classify_assistance(scheme: dict) -> str:
    raw = str(scheme.get("assistance_type") or "").upper()
    scheme_type = str(scheme.get("scheme_type") or "").upper()
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    name = str((api.get("name") or {}).get("en") or "").upper()
    blob = f"{raw} {scheme_type} {name}"
    if "COACHING" in blob:
        return ASSISTANCE_COACHING
    if "FELLOWSHIP" in blob:
        return ASSISTANCE_FELLOWSHIP
    if "SUBSIDY" in blob or "INTEREST SUBSIDY" in blob:
        return ASSISTANCE_SUBSIDY
    if "SCHOLARSHIP" in blob:
        return ASSISTANCE_SCHOLARSHIP
    if raw == ASSISTANCE_LOAN or "LOAN" in scheme_type or "EDUCATIONAL LOAN" in name:
        return ASSISTANCE_LOAN
    if raw in {
        ASSISTANCE_LOAN, ASSISTANCE_SCHOLARSHIP, ASSISTANCE_SUBSIDY,
        ASSISTANCE_FELLOWSHIP, ASSISTANCE_COACHING, ASSISTANCE_OTHER,
    }:
        return raw
    return ASSISTANCE_OTHER


def verification_status(scheme: dict) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    explicit = str(api.get("verificationStatus") or "").upper()
    quality = audit_scheme(scheme)["quality"]
    flagged = bool(scheme.get("verified") is True and api.get("verified") is not False)
    if flagged and quality == "SUFFICIENT":
        return VERIFIED
    if explicit == VERIFIED and flagged:
        return VERIFIED
    if flagged or quality == "PARTIAL" or explicit == "PARTIAL":
        return PARTIAL
    return UNVERIFIED


def is_education_related(scheme: dict) -> bool:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    domain = str(scheme.get("domain") or "").upper()
    category = str(api.get("officialCategory") or "").upper()
    if domain == "EDUCATION" or category == "EDUCATION":
        return True
    purpose = str(scheme.get("purpose") or "").upper()
    scheme_type = str(scheme.get("scheme_type") or "").upper()
    return "EDUCATION" in purpose or "SCHOLAR" in scheme_type or "FELLOW" in scheme_type


def _canonical_id(scheme: dict) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    return str(api.get("id") or scheme.get("scheme_id") or "")


def _name(scheme: dict, lang: str) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    names = api.get("name") if isinstance(api.get("name"), dict) else {}
    return str(names.get(lang) or names.get("en") or _canonical_id(scheme))


def _org(scheme: dict) -> str:
    raw = str(scheme.get("organization") or scheme.get("organization_code") or "OTHER").upper()
    if raw in {"NSFDC", "NBCFDC", "NSKFDC"}:
        return raw
    if "MINISTRY" in raw or "DEPARTMENT" in raw:
        return "MINISTRY/DEPARTMENT"
    return raw or "OTHER"


def _source_url(scheme: dict) -> str:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    url = str(scheme.get("source_url") or api.get("officialUrl") or api.get("sourceUrl") or "")
    if url.lower() in {"", "unknown"}:
        return ""
    return url


def _loan_max(scheme: dict) -> Optional[int]:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    val = api.get("maxLoanAmount")
    try:
        return int(val) if val is not None else None
    except (TypeError, ValueError):
        return None


def _income_limit(scheme: dict, assistance: str) -> Optional[int]:
    if _org(scheme) == "NSFDC" and assistance == ASSISTANCE_LOAN:
        api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
        val = api.get("maxAnnualFamilyIncome")
        try:
            return int(val) if val is not None else NSFDC_LOAN_INCOME_CEILING
        except (TypeError, ValueError):
            return NSFDC_LOAN_INCOME_CEILING
    return None


def _inr(n: int) -> str:
    if n >= 100000:
        lakhs = n / 100000
        if lakhs == int(lakhs):
            return f"₹{int(lakhs)} lakh"
        return f"₹{lakhs:.2f} lakh"
    return f"₹{n:,}"


@lru_cache(maxsize=1)
def education_catalogue() -> tuple[dict, ...]:
    return tuple(s for s in iter_schemes() if is_education_related(s))


def reset_education_catalogue_cache() -> None:
    education_catalogue.cache_clear()


def _amount_fit(assistance: str, loan_max: Optional[int], amount: Optional[float], verified: str) -> str:
    if assistance not in {ASSISTANCE_LOAN, ASSISTANCE_SUBSIDY}:
        return NOT_A_LOAN
    if verified == UNVERIFIED or loan_max is None or amount is None:
        return AMOUNT_UNKNOWN
    if amount > loan_max:
        return OUTSIDE_RANGE
    return WITHIN_RANGE


def _income_fit(income_limit: Optional[int], income: Optional[float], verified: str) -> str:
    if income is None or income_limit is None:
        return INCOME_UNKNOWN
    if verified == UNVERIFIED:
        return INCOME_UNKNOWN
    if income > income_limit:
        return ABOVE_LIMIT
    return WITHIN_LIMIT


def _course_fit(scheme_id: str, assistance: str, course: Optional[str]) -> str:
    if not course:
        return COURSE_UNKNOWN
    token = str(course).replace(" ", "").replace(".", "").upper()
    if scheme_id == "nsfdc-education" and any(k.replace(".", "") in token or token in k for k in _TECHNICAL_COURSE):
        return COURSE_MATCH
    if assistance == ASSISTANCE_LOAN and any(k.replace(".", "") in token for k in _TECHNICAL_COURSE):
        return COURSE_MATCH
    return COURSE_UNKNOWN


def _relevance(assistance: str, verified: str, amount_fit: str, income_fit: str, wants_loan: bool) -> str:
    if not wants_loan:
        if assistance == ASSISTANCE_SCHOLARSHIP:
            return "HIGH" if verified != UNVERIFIED else "MEDIUM"
        if assistance == ASSISTANCE_LOAN:
            return "LOW"
        return "MEDIUM" if verified != UNVERIFIED else "LOW"
    if wants_loan and assistance == ASSISTANCE_LOAN:
        if verified == VERIFIED and amount_fit != OUTSIDE_RANGE and income_fit != ABOVE_LIMIT:
            return "HIGH"
        return "MEDIUM"
    if wants_loan and assistance == ASSISTANCE_SUBSIDY:
        return "MEDIUM"
    return "MEDIUM" if verified != UNVERIFIED else "LOW"


def _wants_nsfdc(query: Optional[str]) -> bool:
    return "nsfdc" in (query or "").lower()


def _wants_loan(query: Optional[str], activity: Optional[str]) -> bool:
    blob = f"{query or ''} {activity or ''}".lower()
    if any(w in blob for w in ("scholarship", "स्कॉलरशिप", "fellowship", "coaching", "कोचिंग")):
        if "loan" not in blob and "लोन" not in blob and "कर्ज" not in blob:
            return False
    return True


def evaluate_education_options(
    *,
    amount: Optional[float],
    income: Optional[float],
    course: Optional[str],
    lang: str,
    query: Optional[str] = None,
    activity: Optional[str] = None,
) -> list[EducationOption]:
    lang = "hi" if lang == "hi" else "en"
    wants_loan = _wants_loan(query, activity)
    nsfdc_only = _wants_nsfdc(query)
    options: list[EducationOption] = []
    for scheme in education_catalogue():
        sid = _canonical_id(scheme)
        if not sid:
            continue
        assistance = classify_assistance(scheme)
        org = _org(scheme)
        if nsfdc_only and org != "NSFDC" and assistance != ASSISTANCE_LOAN:
            # Explicit NSFDC request: keep NSFDC primary; other orgs only as labelled support.
            pass
        status = verification_status(scheme)
        quality = audit_scheme(scheme)["quality"]
        loan_max = _loan_max(scheme) if status != UNVERIFIED else None
        income_limit = _income_limit(scheme, assistance) if status != UNVERIFIED else None
        if org == "NSFDC" and assistance == ASSISTANCE_LOAN:
            loan_max = loan_max or NSFDC_ELS_LOAN_MAX
            income_limit = income_limit or NSFDC_LOAN_INCOME_CEILING
        amount_fit = _amount_fit(assistance, loan_max, amount, status)
        income_fit = _income_fit(income_limit, income, status)
        course_fit = _course_fit(sid, assistance, course)
        why, why_not = _why(
            assistance=assistance,
            status=status,
            org=org,
            name=_name(scheme, lang),
            amount=amount,
            amount_fit=amount_fit,
            income=income,
            income_fit=income_fit,
            income_limit=income_limit,
            loan_max=loan_max,
            lang=lang,
        )
        options.append(
            EducationOption(
                scheme_id=sid,
                scheme_name=_name(scheme, lang),
                organization=org,
                assistance_type=assistance,
                verification_status=status,
                metadata_quality=quality,
                source_url=_source_url(scheme) or (SOURCE_FAQ if org == "NSFDC" else ""),
                loan_amount_max=loan_max,
                income_limit=income_limit,
                amount_fit=amount_fit,
                income_fit=income_fit,
                course_fit=course_fit,
                why_relevant=why,
                why_not=why_not,
                requires_verification=status != VERIFIED,
                relevance=_relevance(assistance, status, amount_fit, income_fit, wants_loan),
                purpose=str(scheme.get("purpose") or ""),
            )
        )
    options.sort(
        key=lambda o: (
            0 if o.organization == "NSFDC" else 1,
            0 if o.assistance_type == ASSISTANCE_LOAN else 1,
            0 if o.verification_status == VERIFIED else 1,
            0 if o.relevance == "HIGH" else 1,
            o.scheme_name.lower(),
        )
    )
    return options


def _why(
    *,
    assistance: str,
    status: str,
    org: str,
    name: str,
    amount: Optional[float],
    amount_fit: str,
    income: Optional[float],
    income_fit: str,
    income_limit: Optional[int],
    loan_max: Optional[int],
    lang: str,
) -> tuple[str, str]:
    hi = lang == "hi"
    why_bits: list[str] = []
    why_not: list[str] = []
    if assistance == ASSISTANCE_LOAN:
        why_bits.append("शिक्षा ऋण" if hi else "education loan")
    elif assistance == ASSISTANCE_SCHOLARSHIP:
        why_bits.append("यह ऋण नहीं, छात्रवृत्ति है" if hi else "scholarship — not a loan")
    elif assistance == ASSISTANCE_SUBSIDY:
        why_bits.append("ब्याज सब्सिडी, ऋण उत्पाद नहीं" if hi else "interest subsidy, not a standalone loan")
    elif assistance == ASSISTANCE_FELLOWSHIP:
        why_bits.append("फेलोशिप, ऋण नहीं" if hi else "fellowship — not a loan")
    elif assistance == ASSISTANCE_COACHING:
        why_bits.append("कोचिंग सहायता, ऋण नहीं" if hi else "coaching support — not a loan")
    else:
        why_bits.append("शिक्षा-संबंधी सहायता" if hi else "other education support")
    why_bits.append(org)
    if status == VERIFIED and amount_fit == WITHIN_RANGE and amount is not None:
        why_bits.append(
            f"आपकी राशि {_inr(int(amount))} प्रकाशित अधिकतम {_inr(loan_max)} के भीतर है" if hi and loan_max
            else f"stated amount {_inr(int(amount))} is within the published maximum of {_inr(loan_max)}" if loan_max
            else (f"amount {_inr(int(amount))} is within the published range" if not hi else f"राशि {_inr(int(amount))} प्रकाशित सीमा में है")
        )
    if status == VERIFIED and income_fit == WITHIN_LIMIT and income is not None and income_limit:
        why_bits.append(
            f"आय {_inr(int(income))} NSFDC की वर्तमान {_inr(income_limit)} सीमा के भीतर है" if hi
            else f"stated income {_inr(int(income))} is within NSFDC's current {_inr(income_limit)} ceiling"
        )
    if amount_fit == OUTSIDE_RANGE and amount is not None and loan_max:
        why_not.append(
            f"राशि {_inr(int(amount))} प्रकाशित अधिकतम {_inr(loan_max)} से अधिक है" if hi
            else f"stated amount {_inr(int(amount))} exceeds the published maximum of {_inr(loan_max)}"
        )
    if income_fit == ABOVE_LIMIT and income is not None and income_limit:
        why_not.append(
            f"आय {_inr(int(income))} NSFDC की वर्तमान {_inr(income_limit)} सीमा से ऊपर है" if hi
            else f"stated income {_inr(int(income))} is above NSFDC's current {_inr(income_limit)} ceiling"
        )
    if status != VERIFIED:
        why_not.append(
            "वर्तमान विवरण की पुष्टि नहीं हो सकी" if hi
            else "current details could not be confirmed"
        )
    return "; ".join(why_bits), "; ".join(why_not)


def _missing(amount: Optional[float], course: Optional[str], income: Optional[float]) -> list[str]:
    missing: list[str] = []
    if amount is None:
        missing.append("requested_amount")
    elif not course or str(course).upper() in {"EDUCATION", "EDUCATION_LOAN", "GENERAL"}:
        missing.append("course")
    elif income is None:
        missing.append("income")
    return missing


def _next_question(missing: list[str], lang: str) -> Optional[str]:
    hi = lang == "hi"
    if "requested_amount" in missing:
        return "पढ़ाई के लिए लगभग कितनी राशि चाहिए?" if hi else "Approximately how much funding do you need?"
    if "course" in missing:
        return "आप कौन-सा कोर्स कर रहे हैं या करना चाहते हैं?" if hi else "What course are you pursuing?"
    if "income" in missing:
        return "आपकी अनुमानित वार्षिक पारिवारिक आय कितनी है?" if hi else "What is your approximate annual family income?"
    return None


def render_education_answer(
    *,
    options: list[EducationOption],
    loans: list[EducationOption],
    support: list[EducationOption],
    amount: Optional[float],
    income: Optional[float],
    course: Optional[str],
    lang: str,
    next_question: Optional[str],
) -> str:
    hi = lang == "hi"
    lines: list[str] = []
    els = next((o for o in loans if o.scheme_id == "nsfdc-education"), None)
    if els:
        if hi:
            lines.append(
                "पढ़ाई के ऋण के लिए NSFDC की शैक्षिक ऋण योजना मुख्य सत्यापित ऋण विकल्प है — "
                "नियमित पूर्णकालिक व्यावसायिक/तकनीकी मान्यता प्राप्त पाठ्यक्रम, भारत या विदेश।"
            )
        else:
            lines.append(
                "NSFDC's Educational Loan Scheme is the main verified loan option I found for "
                "regular full-time professional or technical courses, in India or abroad."
            )
        if els.verification_status == VERIFIED:
            if amount is not None and els.amount_fit == WITHIN_RANGE:
                lines.append(
                    f"₹{_inr(int(amount)).lstrip('₹')} की बताई राशि वर्तमान अधिकतम ऋण {_inr(els.loan_amount_max or NSFDC_ELS_LOAN_MAX)} के भीतर है।"
                    if hi else
                    f"At {_inr(int(amount))}, this is within the current stated maximum loan of {_inr(els.loan_amount_max or NSFDC_ELS_LOAN_MAX)} (or 90% of course fee, whichever is less)."
                )
            elif amount is not None and els.amount_fit == OUTSIDE_RANGE:
                lines.append(
                    f"बताई राशि प्रकाशित अधिकतम से अधिक है।" if hi
                    else "The stated amount is above the published maximum for this scheme."
                )
            if income is not None and els.income_fit == WITHIN_LIMIT:
                lines.append(
                    f"आपकी बताई वार्षिक पारिवारिक आय {_inr(int(income))} NSFDC ऋणों की वर्तमान {_inr(NSFDC_LOAN_INCOME_CEILING)} सीमा के भीतर है, अन्य शर्तों के अधीन।"
                    if hi else
                    f"Your stated annual family income of {_inr(int(income))} is within NSFDC's current {_inr(NSFDC_LOAN_INCOME_CEILING)} income ceiling for loans, subject to the other eligibility requirements."
                )
            elif income is not None and els.income_fit == ABOVE_LIMIT:
                lines.append(
                    f"NSFDC की वर्तमान ऋण आय सीमा {_inr(NSFDC_LOAN_INCOME_CEILING)} है, इसलिए आपकी बताई {_inr(int(income))} उस प्रकाशित सीमा से ऊपर है। मैं NSFDC ELS पात्रता का दावा नहीं कर सकता।"
                    if hi else
                    f"NSFDC's current loan income ceiling is {_inr(NSFDC_LOAN_INCOME_CEILING)}, so your stated {_inr(int(income))} family income is above that published ceiling. I cannot claim NSFDC ELS eligibility based on this information."
                )
            if course and els.course_fit == COURSE_MATCH:
                lines.append(
                    f"{course} एक व्यावसायिक/तकनीकी पाठ्यक्रम के रूप में मेल खाता है।" if hi
                    else f"{course} matches the professional/technical course type this scheme supports."
                )
            lines.append(
                "यह गारंटीशुदा पात्रता नहीं है — जाति प्रमाण पत्र और अन्य शर्तें लागू रहती हैं।"
                if hi else
                "This is not a guarantee of eligibility — an SC caste certificate and the other published conditions still apply."
            )
    other_loans = [o for o in loans if o.scheme_id != "nsfdc-education"]
    if other_loans:
        names = ", ".join(f"{o.scheme_name} ({o.organization})" for o in other_loans[:3])
        lines.append(
            f"कैटलॉग में अन्य ऋण-संबंधी रिकॉर्ड भी हैं, जैसे {names} — ये सत्यापन आवश्यक हैं और इन्हें NSFDC योजना नहीं माना गया।"
            if hi else
            f"The catalogue also lists other loan-related records such as {names}. These require verification and are not NSFDC schemes."
        )
    if support:
        by_type: dict[str, int] = {}
        for o in support:
            by_type[o.assistance_type] = by_type.get(o.assistance_type, 0) + 1
        type_bits = []
        labels = {
            ASSISTANCE_SCHOLARSHIP: ("छात्रवृत्ति", "scholarships"),
            ASSISTANCE_FELLOWSHIP: ("फेलोशिप", "fellowships"),
            ASSISTANCE_COACHING: ("कोचिंग", "coaching"),
            ASSISTANCE_SUBSIDY: ("ब्याज सब्सिडी", "interest subsidies"),
            ASSISTANCE_OTHER: ("अन्य शिक्षा सहायता", "other education assistance"),
        }
        for key, count in by_type.items():
            hi_l, en_l = labels.get(key, (key, key))
            type_bits.append(f"{count} {hi_l}" if hi else f"{count} {en_l}")
        lines.append(
            "मुख्य ऋण विकल्प के अलावा कैटलॉग में अन्य शिक्षा-सहायता रिकॉर्ड हैं ("
            + ", ".join(type_bits)
            + ") — ये ऋण उत्पाद नहीं हैं, और अधिकांश के वर्तमान विवरण की पुष्टि नहीं हो सकी।"
            if hi else
            "Besides the loan option, I also found other education-support records in the catalogue ("
            + ", ".join(type_bits)
            + "). Those are not loan products, and most still require verification because current details could not be confirmed."
        )
    if amount is not None and income is not None:
        rows = []
        for o in (loans + support)[:6]:
            a = {
                WITHIN_RANGE: "Fits" if not hi else "सीमा में",
                OUTSIDE_RANGE: "Outside" if not hi else "सीमा से बाहर",
                NOT_A_LOAN: "Not a loan" if not hi else "ऋण नहीं",
                AMOUNT_UNKNOWN: "Unknown" if not hi else "अज्ञात",
            }.get(o.amount_fit, o.amount_fit)
            i = {
                WITHIN_LIMIT: "Fits" if not hi else "सीमा में",
                ABOVE_LIMIT: "Above" if not hi else "ऊपर",
                INCOME_UNKNOWN: "Unknown / verify" if not hi else "अज्ञात",
            }.get(o.income_fit, o.income_fit)
            v = o.verification_status
            rows.append(f"{o.scheme_name} | {o.assistance_type} | {a} | {i} | {v}")
        if rows:
            header = "योजना | प्रकार | राशि | आय | सत्यापन" if hi else "Scheme | Type | Amount fit | Income fit | Verification"
            lines.append(("तुलना: " if hi else "Comparison: ") + header + " — " + " ; ".join(rows))
    if next_question:
        lines.append(next_question)
    return " ".join(lines)


def build_education_brief(
    *,
    amount: Optional[float],
    income: Optional[float],
    course: Optional[str],
    lang: str,
    query: Optional[str] = None,
    activity: Optional[str] = None,
) -> EducationBrief:
    lang = "hi" if lang == "hi" else "en"
    options = evaluate_education_options(
        amount=amount, income=income, course=course, lang=lang, query=query, activity=activity,
    )
    nsfdc_only = _wants_nsfdc(query)
    loans = [o for o in options if o.assistance_type == ASSISTANCE_LOAN]
    if nsfdc_only:
        primary_loans = [o for o in loans if o.organization == "NSFDC"]
        support = [o for o in options if o not in primary_loans]
    else:
        primary_loans = loans
        support = [o for o in options if o.assistance_type != ASSISTANCE_LOAN]
    missing = _missing(amount, course or activity, income)
    next_q = _next_question(missing, lang)
    answer = render_education_answer(
        options=options,
        loans=primary_loans or loans,
        support=support,
        amount=amount,
        income=income,
        course=course or activity,
        lang=lang,
        next_question=next_q,
    )
    related = []
    for o in (primary_loans or loans) + support:
        if o.scheme_id not in related:
            related.append(o.scheme_id)
    return EducationBrief(
        options=options,
        primary_loan_options=primary_loans or loans,
        other_education_support=support,
        missing=missing,
        next_question=next_q,
        answer=answer,
        related_ids=related,
    )


def _education_gender_fit(scheme_id: str, gender: Optional[str]) -> Optional[str]:
    if not gender:
        return None
    try:
        from app.eligibility_engine import load_scheme
        return gender_fit_role(load_scheme(scheme_id), gender)
    except Exception:
        return "UNKNOWN"


def education_ui_cards(brief: EducationBrief, lang: str, gender: Optional[str] = None) -> list[AssistantUICard]:
    cards: list[AssistantUICard] = []
    ordered = list(brief.primary_loan_options) + list(brief.other_education_support)
    seen: set[str] = set()
    hi = lang == "hi"
    primary_id = next((o.scheme_id for o in brief.primary_loan_options), None)
    for opt in ordered:
        if opt.scheme_id in seen:
            continue
        seen.add(opt.scheme_id)
        if opt.assistance_type != ASSISTANCE_LOAN and len(cards) >= 6:
            if opt.assistance_type == ASSISTANCE_SCHOLARSHIP and sum(
                1 for c in cards if (c.assistanceType or "") == ASSISTANCE_SCHOLARSHIP
            ) >= 2:
                continue
        why: list[dict] = []
        if opt.income_fit == WITHIN_LIMIT and opt.income_limit:
            why.append({
                "kind": "MATCH",
                "text": (
                    f"आपकी पारिवारिक आय {_inr(opt.income_limit)} की प्रकाशित सीमा के भीतर है।"
                    if hi else
                    f"Your family income is within the published ceiling of {_inr(opt.income_limit)}."
                ),
            })
        elif opt.income_fit == ABOVE_LIMIT and opt.income_limit:
            why.append({
                "kind": "MISMATCH",
                "text": (
                    f"आपकी पारिवारिक आय {_inr(opt.income_limit)} की प्रकाशित सीमा से अधिक है।"
                    if hi else
                    f"Your family income is above the published ceiling of {_inr(opt.income_limit)}."
                ),
            })
        elif opt.income_fit == INCOME_UNKNOWN:
            why.append({
                "kind": "INFO",
                "text": "पारिवारिक आय की पुष्टि आवश्यक है।" if hi else "Family income confirmation is required.",
            })
        if opt.amount_fit == WITHIN_RANGE:
            why.append({
                "kind": "MATCH",
                "text": "आपकी बताई राशि योजना की सीमा में है।" if hi else "Your stated amount is within the scheme limit.",
            })
        elif opt.amount_fit == OUTSIDE_RANGE:
            why.append({
                "kind": "MISMATCH",
                "text": "आपकी बताई राशि योजना की सीमा से बाहर है।" if hi else "Your stated amount is outside the scheme limit.",
            })
        elif opt.amount_fit == AMOUNT_UNKNOWN:
            why.append({
                "kind": "INFO",
                "text": "राशि की पुष्टि आवश्यक है।" if hi else "Amount confirmation is required.",
            })
        elif opt.amount_fit == NOT_A_LOAN:
            why.append({
                "kind": "INFO",
                "text": "यह ऋण उत्पाद नहीं है।" if hi else "This is not a loan product.",
            })
        if opt.course_fit == COURSE_MATCH:
            why.append({
                "kind": "MATCH",
                "text": "आपका कोर्स योजना के उद्देश्यों से मेल खाता है।" if hi else "Your course matches this education product.",
            })
        elif opt.course_fit == COURSE_UNKNOWN:
            why.append({
                "kind": "INFO",
                "text": "कोर्स की पुष्टि आवश्यक है।" if hi else "Course confirmation is required.",
            })
        if opt.requires_verification or opt.verification_status != VERIFIED:
            why.append({
                "kind": "INFO",
                "text": opt.why_not or ("सत्यापन आवश्यक है।" if hi else "Verification required."),
            })
        is_primary = bool(primary_id and opt.scheme_id == primary_id and opt.assistance_type == ASSISTANCE_LOAN)
        caption = (
            "दी गई जानकारी के आधार पर सबसे संबंधित"
            if hi and is_primary
            else (
                "Most relevant based on the information provided"
                if is_primary
                else (
                    "आपकी जानकारी के आधार पर मेल खाता विकल्प"
                    if hi
                    else "Matches your details"
                )
            )
        )
        if opt.assistance_type != ASSISTANCE_LOAN:
            caption = opt.why_relevant
            if opt.requires_verification:
                extra = opt.why_not or ("Verification required" if not hi else "सत्यापन आवश्यक")
                if extra.lower() not in caption.lower():
                    caption = f"{caption}. {extra}"
        elif opt.requires_verification or opt.verification_status != VERIFIED:
            caption = opt.why_not or ("Verification required" if not hi else "सत्यापन आवश्यक")
        verified_financials = opt.verification_status == VERIFIED and opt.assistance_type == ASSISTANCE_LOAN
        cards.append(
            AssistantUICard(
                type=AssistantUICardType.SCHEME_CARD,
                schemeId=opt.scheme_id,
                schemeName=opt.scheme_name,
                reason=caption,
                eligible=None,
                organization=opt.organization,
                domain="EDUCATION",
                assistanceType=opt.assistance_type,
                verificationStatus=opt.verification_status,
                fitStatus="MOST_RELEVANT" if is_primary else ("RELATED" if opt.assistance_type != ASSISTANCE_LOAN else "MATCHES_DETAILS"),
                fitReasons=why,
                whySelected=why,
                amountFit=opt.amount_fit,
                incomeFit=opt.income_fit,
                courseFit=opt.course_fit,
                genderFit=_education_gender_fit(opt.scheme_id, gender),
                purposeFit="MATCH",
                eligibilityNotes=opt.why_not if opt.requires_verification else None,
                maxLoanAmount=float(opt.loan_amount_max) if verified_financials and opt.loan_amount_max else None,
                isPrimary=is_primary,
                action="VIEW_DETAILS",
            )
        )
        if len(cards) >= 8:
            break
    if "requested_amount" not in brief.missing and "income" not in brief.missing:
        rows = [
            {
                "schemeName": opt.scheme_name,
                "assistanceType": opt.assistance_type,
                "amountFit": opt.amount_fit,
                "incomeFit": opt.income_fit,
                "verificationStatus": opt.verification_status,
                "schemeId": opt.scheme_id,
            }
            for opt in ordered[:6]
        ]
        if rows:
            cards.append(
                AssistantUICard(
                    type=AssistantUICardType.COMPARISON_CARD,
                    title="तुलना" if hi else "Comparison",
                    rows=rows,
                )
            )
    return cards
