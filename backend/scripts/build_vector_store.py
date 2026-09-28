"""Rebuild the RAG vector index from structured scheme-knowledge chunks.

Production (Render) must run this during build with Hugging Face inference:
  BUILDING_VECTOR_STORE=1 python3 scripts/build_vector_store.py

That uses the existing HF feature-extraction path. It does not load the
local SentenceTransformer weights on Render.
"""

import os
import sys
from pathlib import Path

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.scheme_knowledge import load_knowledge_chunks
from app.rag.vector_store import build_store
from app.rag.embeddings import embed
from app.scheme_catalogue import validate_catalogue

STORE_PATH = Path(__file__).resolve().parent.parent / "data" / "rag" / "vector_store.npz"


def main():
    catalogue_failures = validate_catalogue(
        Path(__file__).resolve().parent.parent / "data" / "schemes"
    )
    blocking = [
        failure for failure in catalogue_failures
        if any(
            issue in {
                "duplicate_scheme_id", "invalid_status",
                "recommendable_missing_source", "missing_scheme_id",
            }
            for issue in failure["issues"]
        )
    ]
    if blocking:
        raise RuntimeError(f"Catalogue validation failed: {blocking[:5]}")
    chunks = load_knowledge_chunks()
    if not chunks:
        raise RuntimeError("No RAG chunks were produced from the scheme catalogue")
    missing_meta = [
        c.chunk_id for c in chunks
        if (
            not c.scheme_id
            or not c.organization
            or not c.assistance_type
            or not c.lifecycle_status
            or not c.provenance_url
        )
    ]
    if missing_meta:
        raise RuntimeError(f"Chunks missing required metadata: {missing_meta[:5]}")

    print(f"Total chunks created: {len(chunks)}")
    schemes = {c.scheme_id for c in chunks}
    orgs: dict[str, int] = {}
    for c in chunks:
        orgs[c.organization] = orgs.get(c.organization, 0) + 1
    print(f"Schemes indexed: {len(schemes)}")
    print(f"Chunks by org: {orgs}")
    print("Building vector store...")
    store = build_store(chunks, embed)
    if store.embeddings.ndim != 2 or store.embeddings.shape[0] != len(chunks):
        raise RuntimeError(f"Embedding/chunk mismatch: {store.embeddings.shape} vs {len(chunks)} chunks")
    if store.embeddings.shape[1] != 384:
        raise RuntimeError(f"Unexpected embedding dimension: {store.embeddings.shape[1]}")
    store.save(STORE_PATH)
    print(f"Saved {store.embeddings.shape} embeddings to {STORE_PATH}")


if __name__ == "__main__":
    main()
