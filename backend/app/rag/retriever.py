"""
app/rag/retriever.py
────────────────────
Provides the search interface for the RAG pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.rag.chunker import Chunk
from app.rag.embeddings import embed
from app.rag.vector_store import VectorStore

_STORE_PATH = Path(__file__).parent.parent.parent / "data" / "rag" / "vector_store.npz"
_STORE: VectorStore | None = None

@dataclass
class RetrievedChunk:
    chunk: Chunk
    similarity_score: float

def _get_store() -> VectorStore:
    global _STORE
    if _STORE is None:
        _STORE = VectorStore.load(_STORE_PATH)
    return _STORE

def retrieve(
    query: str,
    scheme_id_filter: str | None = None,
    top_k: int = 5,
    strict_scheme_filter: bool = False,
    min_similarity: float | None = None,
    organization_filter: str | None = "NSFDC",
    domain_filter: str | None = None,
    assistance_type_filter: str | None = None,
) -> list[RetrievedChunk]:
    """
    Retrieves the most relevant chunks for a query.
    
    Args:
        query: The search text (can be any supported language).
        scheme_id_filter: If provided, affects ranking or filtering based on strict mode.
        top_k: Maximum number of chunks to return.
        strict_scheme_filter: 
            If True and scheme_id_filter is set, ONLY returns chunks from that scheme.
            If False and scheme_id_filter is set, strongly prefers chunks from that 
            scheme by boosting their similarity score, but allows cross-scheme results.
        min_similarity: If provided, drops any chunk with a final similarity score below this.
    """
    store = _get_store()
    if not store.chunks:
        return []
        
    query_vec = embed([query])[0]
    
    # We ask the vector store for more results initially in case we filter many out
    raw_results = store.search(query_vec, top_k=max(20, top_k * 3))
    
    processed_results: list[RetrievedChunk] = []
    
    for chunk, score in raw_results:
        # 1. Apply strict filtering
        if strict_scheme_filter and scheme_id_filter:
            if chunk.scheme_id != scheme_id_filter:
                continue
                
        # 2. Apply metadata filtering (organization, domain, assistance_type)
        if organization_filter and hasattr(chunk, 'organization'):
            if chunk.organization != organization_filter:
                # If organization doesn't match, penalize heavily unless it's an exact scheme ID match
                if not (scheme_id_filter and chunk.scheme_id == scheme_id_filter):
                    score *= 0.5

        if domain_filter and hasattr(chunk, 'domain'):
            # Soft penalty for domain mismatch
            if chunk.domain != "OTHER" and chunk.domain != domain_filter:
                score *= 0.8
                
        if assistance_type_filter and hasattr(chunk, 'assistance_type'):
            if chunk.assistance_type != "OTHER" and chunk.assistance_type != assistance_type_filter:
                score *= 0.8

        final_score = score
        if not strict_scheme_filter and scheme_id_filter:
            if chunk.scheme_id == scheme_id_filter:
                pass # We will handle preferred sorting below
                
        processed_results.append(RetrievedChunk(chunk, final_score))
        
    # Apply preference sorting if strict=False and filter is provided
    if not strict_scheme_filter and scheme_id_filter:
        # Sort by: (matches_scheme: bool, score: float) descending
        processed_results.sort(
            key=lambda rc: (rc.chunk.scheme_id == scheme_id_filter, rc.similarity_score),
            reverse=True
        )
    else:
        # Otherwise just sort by score descending
        processed_results.sort(key=lambda rc: rc.similarity_score, reverse=True)
        
    # Apply min_similarity filter AFTER sorting
    if min_similarity is not None:
        processed_results = [rc for rc in processed_results if rc.similarity_score >= min_similarity]
        
    return processed_results[:top_k]

def retrieve_scheme_context(
    scheme_id: str,
    max_chunks: int | None = None,
) -> list[RetrievedChunk]:
    """
    Returns all chunks for a given scheme_id, ordered by a canonical section order.

    This is the correct retrieval mode for recommendation explanations.
    Unlike retrieve(), this does NOT use semantic similarity — it filters
    purely by scheme_id metadata. This avoids the semantic vacuum of an
    empty query string and ensures the explanation always has complete,
    structured scheme context.

    Use retrieve() for general semantic user questions.
    Use retrieve_scheme_context() when explaining a specific recommendation.

    Args:
        scheme_id: The scheme to retrieve all context for (e.g., "NSFDC_MFS").
        max_chunks: If provided, limits the number of returned chunks.
    """
    # Canonical ordering of sections for explanation readability
    SECTION_ORDER = [
        "overview",
        "eligibility_criteria",
        "financial_terms",
        "eligible_activities",
        "channel_partners",
        "verification_notes",
    ]

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
            return len(SECTION_ORDER)  # unknown sections sort to the end

    matching.sort(key=_section_sort_key)

    if max_chunks is not None:
        matching = matching[:max_chunks]

    return matching
