"""NSFDC scheme comparison / adviser knowledge layer."""

from app.rag.scheme_advisor import (
    COMPARE,
    EXPLAIN,
    OPTIONS,
    build_brief,
    detect_adviser_mode,
    named_scheme_ids,
)


def test_named_scheme_detection():
    assert "nsfdc-term-loan" in named_scheme_ids("Term loan kya hota hai?")
    assert "nsfdc-uny" in named_scheme_ids("Term Loan vs Udyam Nidhi")
    assert "nsfdc-term-loan" in named_scheme_ids("Term Loan vs Udyam Nidhi")


def test_option_comparison_mode():
    mode, _ = detect_adviser_mode("Term loan ke alawa aur kya hai?")
    assert mode == OPTIONS
    mode, _ = detect_adviser_mode("What other options do I have?")
    assert mode == OPTIONS


def test_explain_and_compare_modes():
    assert detect_adviser_mode("Term loan kya hota hai?")[0] == EXPLAIN
    assert detect_adviser_mode("Term Loan vs Udyam Nidhi")[0] == COMPARE


def test_business_discovery_lists_multiple_nsfdc_credit_products():
    brief = build_brief(domain="BUSINESS", amount=None, activity=None, lang="en")
    ids = {f.facts.scheme_id for f in brief.alternatives}
    assert "nsfdc-term-loan" in ids
    assert "nsfdc-uny" in ids
    assert "nsfdc-mfs" in ids
    assert "nsfdc-amy" in ids
    assert "nsfdc-education" not in ids
    assert "term loan" in brief.answer.lower()
    assert "micro finance" in brief.answer.lower()
    assert "udyam" in brief.answer.lower()


def test_one_lakh_considers_microfinance():
    brief = build_brief(domain="BUSINESS", amount=100000, activity=None, lang="en")
    ids = {f.facts.scheme_id for f in ([brief.primary] if brief.primary else []) + brief.alternatives}
    assert "nsfdc-mfs" in ids or "nsfdc-amy" in ids
    answer = brief.answer.lower()
    assert "micro finance" in answer or "aajeevika" in answer


def test_two_lakh_does_not_blindly_pick_only_term_loan():
    brief = build_brief(domain="BUSINESS", amount=200000, activity=None, lang="hi")
    ids = brief.related_ids
    assert "nsfdc-uny" in ids or "nsfdc-term-loan" in ids
    assert "micro finance" in brief.answer.lower() or "सूक्ष्म" in brief.answer or "1.40" in brief.answer


def test_twenty_lakh_term_loan_in_range():
    brief = build_brief(domain="BUSINESS", amount=2000000, activity=None, lang="en")
    assert brief.primary and brief.primary.facts.scheme_id == "nsfdc-term-loan"
    assert "term loan" in brief.answer.lower()
    assert "1.40" in brief.answer or "micro finance" in brief.answer.lower()


def test_education_is_els_not_scholarship():
    brief = build_brief(domain="EDUCATION", amount=None, activity="EDUCATION_LOAN", lang="hi")
    assert brief.primary and brief.primary.facts.scheme_id == "nsfdc-education"
    assert "nsfdc-mfs" not in brief.related_ids
    assert "scholarship" not in brief.answer.lower()
    assert "शैक्षिक" in brief.answer or "educational" in brief.answer.lower()
