"""RAG knowledge + retrieval evaluation. Does not call the LLM."""

from __future__ import annotations

import os

os.environ.setdefault("SAARTHI_MOCK_EMBEDDING", "1")

import pytest

from app.rag.embeddings import embed
from app.rag.language_detect import detect_language_and_intent
from app.rag.query_context import build_retrieval_query
from app.rag.retriever import reset_store, retrieve_ranked_schemes, retrieve
from app.rag.scheme_knowledge import audit_catalogue, load_knowledge_chunks
from app.rag.vector_store import build_store
from app.schemas.chat import ChatProfile

FREE_COACHING = "0070a49e-2e01-554a-8f33-e6ee5648877e"


@pytest.fixture(scope="module")
def rag_store():
    chunks = load_knowledge_chunks()
    store = build_store(chunks, embed)
    reset_store(store)
    yield store
    reset_store(None)


def _top(query: str, profile: ChatProfile | None = None):
    spec = build_retrieval_query(query, profile=profile)
    ranked = retrieve_ranked_schemes(
        query=spec.search_text,
        organization_filter=spec.organization_scope,
        domain_filter=spec.domain,
        assistance_type_filter=spec.assistance_type,
        retrieval_query=spec,
        top_k=5,
    )
    return spec, ranked


def test_corpus_every_scheme_has_chunks_and_metadata(rag_store):
    chunks = rag_store.chunks
    assert chunks
    ids = {c.scheme_id for c in chunks}
    assert all(c.scheme_id for c in chunks)
    assert all(c.organization for c in chunks)
    audit = {a["scheme_id"]: a for a in audit_catalogue()}
    assert FREE_COACHING in audit
    assert audit[FREE_COACHING]["organization"] == "MINISTRY/DEPARTMENT"
    thin = [a for a in audit.values() if a["quality"] == "INSUFFICIENT"]
    assert thin  # catalogue has placeholder ministry records; they must be marked, not invented


def test_devanagari_padhai_is_education_loan_not_generic(rag_store):
    det = detect_language_and_intent("मुझे पढ़ाई के लिए लोन चाहिए")
    assert det.detected_language == "hi"
    assert det.intent == "EDUCATION_LOAN"
    assert det.domain == "EDUCATION"
    spec, ranked = _top("मुझे पढ़ाई के लिए लोन चाहिए")
    assert spec.domain == "EDUCATION"
    assert ranked and ranked[0].scheme_id == "nsfdc-education"
    audit = {a["scheme_id"]: a for a in audit_catalogue()}
    shell = audit["eda53729-9585-58fc-8901-fd767c15ea83"]
    assert shell["quality"] in {"INSUFFICIENT", "PARTIAL"}
    assert "uuid_id" in shell["issues"] or "missing_or_placeholder_description" in shell["issues"]


@pytest.mark.parametrize(
    "query,lang",
    [
        ("I need a loan for rice farming", "en"),
        ("मुझे चावल की खेती के लिए लोन चाहिए", "hi"),
        ("mujhe chawal ki kheti ke liye loan chahiye", "hi"),
    ],
)
def test_agriculture_has_no_grounded_nsfdc_match(rag_store, query, lang):
    det = detect_language_and_intent(query)
    spec, ranked = _top(query)
    assert det.detected_language == lang
    assert spec.assistance_type == "LOAN"
    assert spec.domain == "AGRICULTURE"
    assert spec.organization_scope == "NSFDC"
    assert ranked == []
    ids = {s.scheme_id for s in ranked}
    assert FREE_COACHING not in ids


@pytest.mark.parametrize(
    "query,lang,scheme_id",
    [
        ("I need an education loan", "en", "nsfdc-education"),
        ("mujhe padhai ke liye loan chahiye", "hi", "nsfdc-education"),
    ],
)
def test_education_loan_retrieval(rag_store, query, lang, scheme_id):
    det = detect_language_and_intent(query)
    spec, ranked = _top(query)
    assert det.detected_language == lang
    assert spec.assistance_type == "LOAN"
    assert spec.domain == "EDUCATION"
    assert ranked and ranked[0].scheme_id == scheme_id
    assert ranked[0].organization == "NSFDC"
    assert "scholarship" not in ranked[0].scheme_name.lower()
    assert FREE_COACHING not in {s.scheme_id for s in ranked}


def test_amount_followup_keeps_agriculture_context(rag_store):
    profile = ChatProfile(activity="RICE_FARMING", estimatedProjectCost=200000, projectType=None)
    spec, ranked = _top("2 lakh rupaye", profile)
    assert spec.domain == "AGRICULTURE"
    assert spec.requested_amount == 200000
    assert spec.activity == "RICE_FARMING"
    assert ranked == []


def test_btech_keeps_education_loan(rag_store):
    profile = ChatProfile(projectType="EDUCATION", activity="BTECH")
    spec, ranked = _top("BTech", profile)
    assert spec.domain == "EDUCATION"
    assert spec.assistance_type == "LOAN"
    assert spec.education_course == "BTECH"
    assert ranked[0].scheme_id == "nsfdc-education"
    names = " ".join(s.scheme_name.lower() for s in ranked)
    assert "scholarship" not in names
    assert "coaching" not in names


def test_agriculture_negative_not_coaching_or_scholarship(rag_store):
    _, ranked = _top("maine chawal ki kheti ke liye loan manga tha")
    assert ranked == []
    chunks = retrieve("chawal kheti loan", organization_filter="NSFDC", domain_filter="AGRICULTURE", assistance_type_filter="LOAN")
    assert all(c.chunk.scheme_id != FREE_COACHING for c in chunks)
    assert all("scholarship" not in c.chunk.scheme_name.lower() for c in chunks)
    assert all("coach" not in c.chunk.scheme_name.lower() for c in chunks)


def test_education_negative_not_agriculture_or_coaching(rag_store):
    _, ranked = _top("mujhe padhai ke liye loan chahiye")
    for s in ranked:
        assert s.organization == "NSFDC"
        assert s.scheme_id == "nsfdc-education" or s.domain == "EDUCATION"
        assert s.assistance_type == "LOAN"
        assert s.scheme_id != "nsfdc-term-loan"
        assert "coach" not in s.scheme_name.lower()


def test_business_loan_with_two_lakh(rag_store):
    spec, ranked = _top("mujhe business ke liye loan chahiye")
    assert spec.domain == "BUSINESS"
    assert spec.organization_scope == "NSFDC"
    assert ranked
    assert ranked[0].organization == "NSFDC"
    assert ranked[0].assistance_type == "LOAN"
    assert ranked[0].scheme_id != "nsfdc-education"
    profile = ChatProfile(activity="GENERAL_BUSINESS", estimatedProjectCost=200000)
    _, ranked = _top("2 lakh", profile)
    ids = [s.scheme_id for s in ranked]
    assert "nsfdc-education" not in ids
    assert FREE_COACHING not in ids
    assert ranked[0].scheme_id == "nsfdc-term-loan"


def test_dairy_and_poultry_not_forced_to_gbs(rag_store):
    for q, act in (("dairy farming loan", "DAIRY_FARMING"), ("poultry loan", "POULTRY")):
        profile = ChatProfile(activity=act)
        _, ranked = _top(q, profile)
        assert ranked == []


def test_ambiguous_loan_does_not_return_coaching(rag_store):
    det = detect_language_and_intent("mujhe loan chahiye")
    assert det.intent == "GENERAL_LOAN"
    _, ranked = _top("mujhe loan chahiye")
    assert ranked == []


def test_scheme_documents_and_eligibility_sections(rag_store):
    from app.rag.retriever import retrieve_scheme_context
    ctx = retrieve_scheme_context("nsfdc-education")
    sections = {c.chunk.section for c in ctx}
    assert "documents" in sections
    assert "eligibility_criteria" in sections or "education_criteria" in sections
    assert all(c.chunk.scheme_id == "nsfdc-education" for c in ctx)


def test_channel_partner_chunks_exist_for_term_loan(rag_store):
    from app.rag.retriever import retrieve_scheme_context
    ctx = retrieve_scheme_context("nsfdc-term-loan")
    sections = {c.chunk.section for c in ctx}
    assert "channel_partners" in sections
    assert all(c.chunk.organization == "NSFDC" for c in ctx)


def test_yes_followup_does_not_change_domain(rag_store):
    profile = ChatProfile(activity="RICE_FARMING", estimatedProjectCost=200000)
    spec, _ = _top("haan", profile)
    assert spec.domain == "AGRICULTURE"
    assert spec.requested_amount == 200000


def test_short_activity_replies_keep_loan_intent(rag_store):
    agri = ChatProfile(activity="FARMING")
    rice_spec, rice_ranked = _top("chawal", agri)
    assert rice_spec.domain == "AGRICULTURE"
    assert rice_ranked == []
    rice2, _ = _top("rice", agri)
    assert rice2.domain == "AGRICULTURE"
    edu = ChatProfile(projectType="EDUCATION", activity="EDUCATION_LOAN")
    btech_spec, btech_ranked = _top("BTech", edu)
    assert btech_spec.domain == "EDUCATION"
    assert btech_ranked[0].scheme_id == "nsfdc-education"
    nahi_spec, _ = _top("nahi", ChatProfile(activity="RICE_FARMING"))
    assert nahi_spec.domain == "AGRICULTURE"
