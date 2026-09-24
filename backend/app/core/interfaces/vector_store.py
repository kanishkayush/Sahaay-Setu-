from typing import Protocol, List, Tuple
import numpy as np
from pathlib import Path
from app.rag.chunker import Chunk

class VectorStoreProtocol(Protocol):
    def search(self, query_vec: np.ndarray, top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """Returns top_k chunks sorted by similarity descending."""
        ...

    def save(self, path: Path) -> None:
        """Saves the vector store to disk (if applicable)."""
        ...
