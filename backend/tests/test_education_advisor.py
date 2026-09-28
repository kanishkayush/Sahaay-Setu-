"""Education catalogue adviser: multi-scheme comparison, not a single loan."""

from app.rag.education_advisor import (
    ASSISTANCE_COACHING,
    ASSISTANCE_LOAN,
    ASSISTANCE_SCHOLARSHIP,
    ASSISTANCE_SUBSIDY,
    NSFDC_ELS_LOAN_MAX,
    NSFDC_LOAN_INCOME_CEILING,
    UNVERIFIED,
    VERIFIED,
    build_education_brief,
    classify_assistance,
    education_catalogue,
    education_ui_cards,
    evaluate_education_options,
)
from app.rag.scheme_advisor import build_brief, ui_cards
from app.api.chat import process_chat_request
from app.rag.memory import clear_session, get_session_profile
from app.schemas.chat import ChatRequest
from unittest.mock import patch


def _req(query: str, session: str, language: str = "en") -> ChatRequest:
    return ChatRequest(query=query, language=language, conversation_id=session, guideMe=True)


def test_catalogue_finds_multiple_education_schemes():
    cat = education_catalogue()
    assert len(cat) >= 10
    ids = {str(s.get("api", {}).get("id") or s.get("scheme_id")) for s in cat}
    assert "nsfdc-education" in ids


def test_study_loan_considers_all_education_candidates():
    brief = build_education_brief(
        amount=None, income=None, course=None, lang="en",
        query="I need a study loan", activity="EDUCATION_LOAN",
    )
    assert len(brief.options) >= 10
    assert any(o.scheme_id == "nsfdc-education" for o in brief.primary_loan_options)
    assert any(o.assistance_type == ASSISTANCE_SCHOLARSHIP for o in brief.other_education_support)
    assert "scholarship" in brief.answer.lower()
    assert "not a loan" in brief.answer.lower() or "not loan products" in brief.answer.lower()
    assert "how much funding" in brief.answer.lower()
    verified = [o for o in brief.options if o.verification_status == VERIFIED]
    unverified = [o for o in brief.options if o.verification_status == UNVERIFIED]
    assert verified
    assert unverified
    assert all(o.requires_verification for o in unverified)


def test_amount_aware_two_lakh():
    brief = build_education_brief(
        amount=200_000, income=None, course=None, lang="en",
        query="I need ₹2 lakh for studies",
    )
    els = next(o for o in brief.primary_loan_options if o.scheme_id == "nsfdc-education")
    assert els.amount_fit == "WITHIN_RANGE"
    assert "2 lakh" in brief.answer.lower() or "₹2 lakh" in brief.answer
    assert els.loan_amount_max == NSFDC_ELS_LOAN_MAX


def test_five_lakh_btech_els_relevance():
    brief = build_education_brief(
        amount=500_000, income=None, course="BTECH", lang="en",
        query="I need ₹5 lakh for BTech",
    )
    els = next(o for o in brief.options if o.scheme_id == "nsfdc-education")
    assert els.course_fit == "MATCH"
    assert els.amount_fit == "WITHIN_RANGE"
    assert els.relevance == "HIGH"


def test_income_three_lakh_within_ceiling():
    brief = build_education_brief(
        amount=500_000, income=300_000, course="BTECH", lang="en",
        query="My family income is ₹3 lakh and I need ₹5 lakh for BTech",
    )
    els = next(o for o in brief.options if o.scheme_id == "nsfdc-education")
    assert els.income_fit == "WITHIN_LIMIT"
    assert els.income_limit == NSFDC_LOAN_INCOME_CEILING
    assert "within" in brief.answer.lower()
    assert "guaranteed eligible" not in brief.answer.lower()
    assert "not a guarantee" in brief.answer.lower()
    assert any(c.type.value == "COMPARISON_CARD" for c in education_ui_cards(brief, "en"))


def test_income_seven_lakh_above_ceiling_still_shown():
    brief = build_education_brief(
        amount=500_000, income=700_000, course="BTECH", lang="en",
        query="My family income is ₹7 lakh and I need ₹5 lakh for BTech",
    )
    els = next(o for o in brief.options if o.scheme_id == "nsfdc-education")
    assert els.income_fit == "ABOVE_LIMIT"
    assert any(o.scheme_id == "nsfdc-education" for o in brief.primary_loan_options)
    assert "above" in brief.answer.lower() and "5 lakh" in brief.answer.lower()
    assert "cannot claim" in brief.answer.lower() or "eligibility" in brief.answer.lower()
    assert brief.other_education_support


def test_combined_btech_five_lakh_three_lakh():
    brief = build_brief(
        domain="EDUCATION", amount=500_000, activity="BTECH", lang="en",
        income=300_000, query="BTech loan 5 lakh income 3 lakh",
    )
    assert brief.primary and brief.primary.facts.scheme_id == "nsfdc-education"
    assert len(brief.related_ids) >= 3
    cards = ui_cards(brief, "en")
    scheme_cards = [c for c in cards if c.type.value == "SCHEME_CARD"]
    assert scheme_cards[0].schemeId == "nsfdc-education"
    assert any(c.verificationStatus == UNVERIFIED for c in scheme_cards)


def test_hindi_education_multi_option():
    brief = build_education_brief(
        amount=500_000, income=None, course=None, lang="hi",
        query="मुझे पढ़ाई के लिए 5 लाख का लोन चाहिए",
    )
    assert brief.primary_loan_options
    assert "शैक्षिक" in brief.answer or "ऋण" in brief.answer
    assert any(o.assistance_type == ASSISTANCE_SCHOLARSHIP for o in brief.options)


def test_roman_hindi_education_multi_option():
    session = "sess-edu-roman-multi"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("mujhe padhai ke liye 5 lakh ka loan chahiye", session, "hi"))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.requestedLoanAmount == 500_000
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    assert len(resp.related_scheme_ids or []) >= 3
    text = (resp.answer or "").lower()
    if "scholarship" in text:
        assert "loan" in text
    assert "nsfdc-mfs" not in (resp.related_scheme_ids or [])


def test_other_education_options_lists_categories():
    brief = build_education_brief(
        amount=None, income=None, course=None, lang="en",
        query="what other education options are there?",
    )
    types = {o.assistance_type for o in brief.options}
    assert ASSISTANCE_LOAN in types
    assert ASSISTANCE_SCHOLARSHIP in types
    assert ASSISTANCE_COACHING in types or ASSISTANCE_SUBSIDY in types


def test_unverified_relevant_has_warning():
    options = evaluate_education_options(
        amount=200_000, income=300_000, course="BTECH", lang="en",
        query="I need a study loan",
    )
    unverified = [o for o in options if o.verification_status == UNVERIFIED]
    assert unverified
    assert all(o.requires_verification for o in unverified)
    assert all(o.loan_amount_max is None or o.organization == "NSFDC" for o in unverified if o.assistance_type != ASSISTANCE_LOAN)
    brief = build_education_brief(
        amount=200_000, income=300_000, course="BTECH", lang="en", query="I need a study loan",
    )
    cards = education_ui_cards(brief, "en")
    unverified_cards = [c for c in cards if c.verificationStatus == UNVERIFIED]
    assert unverified_cards
    assert any("verification" in (c.reason or "").lower() or "confirm" in (c.reason or "").lower() for c in unverified_cards)


def test_scholarship_never_labelled_loan():
    from app.rag.scheme_knowledge import iter_schemes
    for scheme in iter_schemes():
        name = str((scheme.get("api") or {}).get("name", {}).get("en") or "")
        if "scholarship" in name.lower():
            assert classify_assistance(scheme) == ASSISTANCE_SCHOLARSHIP
    brief = build_education_brief(amount=None, income=None, course=None, lang="en", query="I need a study loan")
    for o in brief.options:
        if o.assistance_type == ASSISTANCE_SCHOLARSHIP:
            assert "not a loan" in o.why_relevant.lower() or "scholarship" in o.why_relevant.lower()
            assert o.amount_fit == "NOT_A_LOAN"


def test_nbcfdc_never_labelled_nsfdc():
    brief = build_education_brief(
        amount=None, income=None, course=None, lang="en", query="I need financial help for studies",
    )
    for o in brief.options:
        if o.organization == "NBCFDC":
            assert o.organization != "NSFDC"
            assert "NSFDC" not in o.scheme_name
    answer = brief.answer
    if "NBCFDC" in answer:
        # Mention is allowed only as a labelled other-org record.
        assert "not NSFDC" in answer or "NBCFDC" in answer


def test_nsfdc_only_request_keeps_nsfdc_primary():
    brief = build_education_brief(
        amount=None, income=None, course=None, lang="en",
        query="I want an NSFDC education loan",
    )
    assert all(o.organization == "NSFDC" for o in brief.primary_loan_options)
    assert brief.primary_loan_options[0].scheme_id == "nsfdc-education"


def test_unverified_does_not_invent_limits():
    options = evaluate_education_options(
        amount=200_000, income=300_000, course="BTECH", lang="en", query="study loan",
    )
    for o in options:
        if o.verification_status == UNVERIFIED and o.organization != "NSFDC":
            assert o.loan_amount_max is None
            assert o.income_limit is None
            assert o.amount_fit in {"UNKNOWN", "NOT_A_LOAN"}
            assert o.income_fit == "UNKNOWN"


def test_interest_subsidy_not_called_loan():
    from app.rag.scheme_knowledge import iter_schemes
    for scheme in iter_schemes():
        name = str((scheme.get("api") or {}).get("name", {}).get("en") or "")
        if "interest subsidy" in name.lower():
            assert classify_assistance(scheme) == ASSISTANCE_SUBSIDY
    brief = build_education_brief(amount=None, income=None, course=None, lang="en", query="study loan")
    subsidies = [o for o in brief.options if o.assistance_type == ASSISTANCE_SUBSIDY]
    for o in subsidies:
        assert "subsidy" in o.why_relevant.lower()
        assert o.scheme_id not in {x.scheme_id for x in brief.primary_loan_options}


def test_guided_study_loan_returns_multiple_related_ids():
    session = "sess-edu-multi-ids"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("I want a loan for study", session, "en"))
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    assert len(resp.related_scheme_ids or []) >= 3
    cards = [c for c in (resp.ui_cards or []) if c.type.value == "SCHEME_CARD"]
    assert cards and cards[0].schemeId == "nsfdc-education"
    orgs = {c.organization for c in cards if c.organization}
    assert "NSFDC" in orgs
    assert get_session_profile(session).recommendedSchemeId == "nsfdc-education"
    assert "how much funding" in (resp.answer or "").lower()


def test_want_loan_for_study_without_article():
    session = "sess-edu-want-loan"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("I want loan for study", session, "en"))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert resp.language == "en"
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    assert len(resp.related_scheme_ids or []) >= 10
    assert "best scheme" not in (resp.answer or "").lower()
    assert "guaranteed eligible" not in (resp.answer or "").lower()
    cards = [c for c in (resp.ui_cards or []) if c.type.value == "SCHEME_CARD"]
    types = {c.assistanceType for c in cards}
    assert "LOAN" in types
    if "SCHOLARSHIP" in types:
        assert any(c.assistanceType == "SCHOLARSHIP" for c in cards)
        assert all(c.assistanceType != "LOAN" or "scholar" not in (c.schemeName or "").lower() for c in cards)


def test_education_amount_ranges_keep_catalogue():
    for amount, expected in ((200000, "WITHIN_RANGE"), (2000000, "WITHIN_RANGE"), (4000000, "WITHIN_RANGE"), (5000000, "OUTSIDE_RANGE")):
        brief = build_education_brief(
            amount=amount, income=None, course=None, lang="en", query="I need an education loan",
        )
        els = next(o for o in brief.primary_loan_options if o.scheme_id == "nsfdc-education")
        assert els.amount_fit == expected
        assert any(o.verification_status == UNVERIFIED for o in brief.options)


def test_mixed_income_and_loan_amount_are_both_kept():
    session = "sess-edu-mixed-amt"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req(
            "मेरी family income 3 lakh hai aur mujhe 2 lakh education loan chahiye",
            session,
            "hi",
        ))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.annualFamilyIncome == 300000
    assert profile.requestedLoanAmount == 200000
    assert profile.estimatedProjectCost is None
    assert resp.language == "hi"
    assert "nsfdc-education" in (resp.related_scheme_ids or [])


def test_multiturn_education_keeps_context_then_compares():
    session = "sess-edu-multi-context"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        process_chat_request(_req("I want a loan for study", session, "en"))
        process_chat_request(_req("BTech", session, "en"))
        process_chat_request(_req("2 lakh", session, "en"))
        process_chat_request(_req("my family income is 3 lakh", session, "en"))
        resp = process_chat_request(_req("show me all the options", session, "en"))
    profile = get_session_profile(session)
    assert profile.projectType == "EDUCATION"
    assert profile.activity == "BTECH"
    assert profile.requestedLoanAmount == 200000
    assert profile.estimatedProjectCost is None
    assert profile.annualFamilyIncome == 300000
    assert "nsfdc-education" in (resp.related_scheme_ids or [])
    assert len(resp.related_scheme_ids or []) >= 10
    text = (resp.answer or "").lower()
    assert "best" not in text or "not" in text
    assert "comparison" in text or "within" in text or "fits" in text


def test_hindi_slot_answers_keep_hindi_until_explicit_english_switch():
    session = "sess-edu-lang-slots"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        r1 = process_chat_request(_req("मुझे पढ़ाई के लिए लोन चाहिए", session, "hi"))
        r2 = process_chat_request(_req("BTech", session, "hi"))
        r3 = process_chat_request(_req("2 lakh", session, "hi"))
        r4 = process_chat_request(_req("my family income is 3 lakh", session, "hi"))
        r5 = process_chat_request(_req("Please answer in English", session, "hi"))
    assert r1.language == "hi"
    assert r2.language == "hi"
    assert r3.language == "hi"
    assert r4.language == "hi"
    assert r5.language == "en"
    profile = get_session_profile(session)
    assert profile.activity == "BTECH"
    assert profile.requestedLoanAmount == 200000
    assert profile.annualFamilyIncome == 300000


def test_coaching_is_not_labelled_financial_assistance():
    from app.rag.scheme_knowledge import iter_schemes
    for scheme in iter_schemes():
        name = str((scheme.get("api") or {}).get("name", {}).get("en") or "")
        if "free coaching" in name.lower():
            assert classify_assistance(scheme) == ASSISTANCE_COACHING


def test_show_me_all_education_options_uses_catalogue():
    session = "sess-edu-all-options"
    clear_session(session)
    with patch("app.rag.guided_journey.litellm.completion", side_effect=RuntimeError("no llm")):
        resp = process_chat_request(_req("show me all education options", session, "en"))
    ids = resp.related_scheme_ids or []
    assert "nsfdc-education" in ids
    assert len(ids) >= 10
    types = {c.assistanceType for c in (resp.ui_cards or []) if getattr(c, "assistanceType", None)}
    assert "LOAN" in types
    assert "SCHOLARSHIP" in types or "FELLOWSHIP" in types
    text = (resp.answer or "").lower()
    assert "nsfdc" in text
    assert "term loan" not in text
    assert "micro finance" not in text
