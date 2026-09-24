"""
app/rag/vector_store.py
───────────────────────
Numpy-backed vector store for RAG chunks.
Stores embeddings and chunk metadata in an .npz file.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Tuple

import numpy as np

from app.rag.chunker import Chunk
from app.core.interfaces.vector_store import VectorStoreProtocol

class VectorStore(VectorStoreProtocol):
    def __init__(self, embeddings: np.ndarray, chunks: list[Chunk]):
        self.embeddings = embeddings
        self.chunks = chunks
        
        # Pre-compute norms for faster cosine similarity
        if len(self.embeddings) > 0:
            self.norms = np.linalg.norm(self.embeddings, axis=1, keepdims=True)
            # Avoid division by zero
            self.norms[self.norms == 0] = 1.0
        else:
            self.norms = np.array([])

    @classmethod
    def load(cls, path: Path) -> VectorStore:
        if not path.exists():
            return cls(np.array([]), [])
            
        data = np.load(path)
        embeddings = data["embeddings"]
        metadata_json = data["metadata"]
        
        chunks = []
        metadata_list = json.loads(str(metadata_json))
        for m in metadata_list:
            chunks.append(Chunk(**m))
            
        return cls(embeddings, chunks)

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        metadata_list = [c.to_dict() for c in self.chunks]
        metadata_json = json.dumps(metadata_list)
        
        np.savez_compressed(
            path,
            embeddings=self.embeddings,
            metadata=metadata_json,
        )

    def search(self, query_vec: np.ndarray, top_k: int = 5) -> list[tuple[Chunk, float]]:
        """
        Returns top_k chunks sorted by cosine similarity descending.
        query_vec should be shape (384,).
        """
        if len(self.embeddings) == 0:
            return []
            
        # Cosine similarity: dot(A, B) / (norm(A) * norm(B))
        query_norm = np.linalg.norm(query_vec)
        if query_norm == 0:
            query_norm = 1.0
            
        dot_products = np.dot(self.embeddings, query_vec)
        similarities = dot_products / (self.norms.squeeze() * query_norm)
        
        # Get top_k indices
        k = min(top_k, len(self.chunks))
        # argpartition is faster than argsort for finding top k, but doesn't sort them
        if k < len(similarities):
            top_k_idx = np.argpartition(similarities, -k)[-k:]
            # Sort just the top k
            top_k_idx = top_k_idx[np.argsort(-similarities[top_k_idx], kind="stable")]
        else:
            top_k_idx = np.argsort(-similarities, kind="stable")
            
        results = []
        for idx in top_k_idx:
            results.append((self.chunks[idx], float(similarities[idx])))
            
        return results

def build_store(chunks: list[Chunk], embed_fn) -> VectorStore:
    """Builds a new vector store from chunks and an embedding function."""
    texts = [c.text for c in chunks]
    embeddings = embed_fn(texts)
    return VectorStore(embeddings, chunks)
