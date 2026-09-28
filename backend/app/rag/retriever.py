"""
app/rag/retriever.py
────────────────────
Metadata-first retrieval: organization / assistance / domain filters run
BEFORE semantic top-k. Chunks are then aggregated to scheme level.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from app.eligibility_engine import load_scheme
from app.rag.chunker import Chunk
from app.rag.embeddings import embed
from app.rag.query_context import RetrievalQuery
from app.recommendation_engine import RelevanceQuery, scheme_relevance_priority
from app.rag.vector_store import VectorStore

_STORE_PATH = Path(__file__).parent.parent.parent / "data" / "rag" / "vector_store.npz"
_STORE: VectorStore | None = None

_TOKEN_RE = re.compile(r"[a-z0-9\u0900-\u097f]+", re.IGNORECASE)

SECTION_ORDER = [
    "overview",
    "purpose",
    "assistance_type",
    "eligibility_criteria",
    "financial_terms",
    "eligible_activities",
    "income_criteria",
    "education_criteria",
    "documents",
    "repayment",
    "channel_partners",
    "application_process",
    "limitations",
    "verification_notes",
    "source",
]


@dataclass
class RetrievedChunk:
    chunk: Chunk
    similarity_score: float


@dataclass
class RankedScheme:
    scheme_id: str
    scheme_name: str
    organization: str
    domain: str
    assistance_type: str
    score: float
    relevance_priority: int
    chunks: list[RetrievedChunk]
    semantic_score: float = 0.0
    lexical_score: float = 0.0
    evidence_count: int = 0
    lifecycle_status: str = "UNCLEAR_STATUS"
    why_retrieved: str = ""


def _get_store() -> VectorStore:
    global _STORE
    if _STORE is None:
        _STORE = VectorStore.load(_STORE_PATH)
    return _STORE


def reset_store(store: VectorStore | None = None) -> None:
    """Test helper: inject or drop the cached index."""
    global _STORE
    _STORE = store


def _tokens(text: str) -> set[str]:
    return {t for t in _TOKEN_RE.findall((text or "").lower()) if len(t) > 2}


def _lexical_score(query: str, chunk: Chunk) -> float:
    q = _tokens(query)
    if not q:
        return 0.0
    blob = f"{chunk.scheme_name} {chunk.text} {chunk.domain} {chunk.assistance_type} {chunk.purpose}"
    c = _tokens(blob)
    if not c:
        return 0.0
    return len(q & c) / len(q)


def _keep_chunk(
    chunk: Chunk,
    organization_filter: str | None,
    relevance: RelevanceQuery | None,
) -> bool:
    if organization_filter:
        if chunk.organization != organization_filter:
            return False
    if relevance is None:
        return True
    try:
        scheme = load_scheme(chunk.scheme_id)
    except Exception:
        return False
    return scheme_relevance_priority(scheme, relevance) > 0


def retrieve(
    query: str,
    scheme_id_filter: str | None = None,
    top_k: int = 5,
    strict_scheme_filter: bool = False,
    min_similarity: float | None = None,
    organization_filter: str | None = "NSFDC",
    domain_filter: str | None = None,
    assistance_type_filter: str | None = None,
    retrieval_query: RetrievalQuery | None = None,
) -> list[RetrievedChunk]:
    ranked = retrieve_ranked_schemes(
        query=query,
        scheme_id_filter=scheme_id_filter,
        top_k=max(3, top_k),
        strict_scheme_filter=strict_scheme_filter,
        min_similarity=min_similarity,
        organization_filter=organization_filter,
        domain_filter=domain_filter,
        assistance_type_filter=assistance_type_filter,
        retrieval_query=retrieval_query,
    )
    out: list[RetrievedChunk] = []
    for scheme in ranked:
        out.extend(scheme.chunks[:2])
        if len(out) >= top_k:
            break
    return out[:top_k]


def retrieve_ranked_schemes(
    query: str,
    scheme_id_filter: str | None = None,
    top_k: int = 5,
    strict_scheme_filter: bool = False,
    min_similarity: float | None = None,
    organization_filter: str | None = "NSFDC",
    domain_filter: str | None = None,
    assistance_type_filter: str | None = None,
    retrieval_query: RetrievalQuery | None = None,
) -> list[RankedScheme]:
    store = _get_store()
    if not store.chunks:
        return []

    search_text = retrieval_query.search_text if retrieval_query else query
    amount = retrieval_query.requested_amount if retrieval_query else None
    domain = (retrieval_query.domain if retrieval_query else None) or domain_filter
    assistance = (
        (retrieval_query.assistance_type if retrieval_query else None)
        or assistance_type_filter
        or "LOAN"
    )
    org = (
        (retrieval_query.organization_scope if retrieval_query else None)
        or organization_filter
    )
    if org == "":
        org = None
    if not scheme_id_filter and (not domain or str(domain).upper() == "OTHER"):
        return []
    relevance = None
    if domain or assistance == "LOAN":
        relevance = RelevanceQuery(
            assistance_type=assistance or "LOAN",
            domain=domain,
            activity=retrieval_query.activity if retrieval_query else None,
            amount_inr=amount,
        )

    query_vec = embed([search_text])[0]

    def rank_for_org(org_filter: str | None) -> list[RankedScheme]:
        def keep(chunk: Chunk) -> bool:
            if strict_scheme_filter and scheme_id_filter and chunk.scheme_id != scheme_id_filter:
                return False
            return _keep_chunk(chunk, org_filter, relevance)

        raw = store.search(query_vec, top_k=max(80, top_k * 12), keep=keep)
        by_scheme: dict[str, RankedScheme] = {}
        for chunk, cosine in raw:
            if scheme_id_filter and strict_scheme_filter and chunk.scheme_id != scheme_id_filter:
                continue
            try:
                scheme = load_scheme(chunk.scheme_id)
                priority = scheme_relevance_priority(scheme, relevance) if relevance else 1
            except Exception:
                continue
            if relevance and priority <= 0:
                continue
            lexical = _lexical_score(search_text, chunk)
            quality_penalty = 0.0 if chunk.metadata_quality == "SUFFICIENT" else (
                -4.0 if chunk.metadata_quality == "INSUFFICIENT" else -1.0
            )
            combined = (priority * 10.0) + (lexical * 4.0) + (float(cosine) * 1.0) + quality_penalty
            rc = RetrievedChunk(chunk, combined)
            existing = by_scheme.get(chunk.scheme_id)
            if existing is None:
                by_scheme[chunk.scheme_id] = RankedScheme(
                    scheme_id=chunk.scheme_id,
                    scheme_name=chunk.scheme_name,
                    organization=chunk.organization,
                    domain=chunk.domain,
                    assistance_type=chunk.assistance_type,
                    score=combined,
                    relevance_priority=priority,
                    chunks=[rc],
                    semantic_score=float(cosine),
                    lexical_score=lexical,
                    evidence_count=1,
                    lifecycle_status=chunk.lifecycle_status,
                    why_retrieved=(
                        f"purpose/domain compatibility={priority}; "
                        f"semantic={float(cosine):.3f}; lexical={lexical:.3f}"
                    ),
                )
            else:
                existing.chunks.append(rc)
                existing.evidence_count += 1
                if combined > existing.score:
                    existing.score = combined
                if float(cosine) > existing.semantic_score:
                    existing.semantic_score = float(cosine)
                if lexical > existing.lexical_score:
                    existing.lexical_score = lexical
                if priority > existing.relevance_priority:
                    existing.relevance_priority = priority

        ranked_local = list(by_scheme.values())
        ranked_local.sort(key=lambda s: (s.relevance_priority, s.score), reverse=True)
        if min_similarity is not None:
            ranked_local = [s for s in ranked_local if s.score >= min_similarity]
        for item in ranked_local:
            item.chunks.sort(key=lambda rc: rc.similarity_score, reverse=True)
            # Scheme-level evidence: several moderately relevant sections should
            # beat a single accidental chunk without letting chunk count dominate.
            supporting = [rc.similarity_score for rc in item.chunks[1:3]]
            item.score += 0.15 * sum(supporting)
            item.why_retrieved += f"; supporting_sections={min(item.evidence_count, 3)}"
        ranked_local.sort(key=lambda s: (s.relevance_priority, s.score), reverse=True)
        return ranked_local

    # NSFDC-first: prefer that organisation, then other verified compatible schemes.
    ranked = rank_for_org(org)
    if not ranked and org:
        ranked = rank_for_org(None)
    return ranked[:top_k]


def retrieve_scheme_context(
    scheme_id: str,
    max_chunks: int | None = None,
) -> list[RetrievedChunk]:
    store = _get_store()
    if not store.chunks:
        return []

    matching = [
        RetrievedChunk(chunk=c, similarity_score=1.0)
        for c in store.chunks
        if c.scheme_id == scheme_id
    ]

    def _section_sort_key(rc: RetrievedChunk) -> int:
        try:
            return SECTION_ORDER.index(rc.chunk.section)
        except ValueError:
            return len(SECTION_ORDER)

    matching.sort(key=_section_sort_key)
    if max_chunks is not None:
        matching = matching[:max_chunks]
    return matching
