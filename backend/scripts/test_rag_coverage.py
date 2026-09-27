import os
import sys
import numpy as np

# Fix python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.api import scheme_loader
from app.rag.vector_store import VectorStore

STORE_PATH = "/Users/kanishkshahi/SIH_2026_RAG/backend/data/rag/vector_store.npz"

def main():
    # 1. Get production scheme IDs (internal IDs)
    catalogue = scheme_loader.get_scheme_catalogue()
    print(f"Total schemes in API catalogue: {len(catalogue)}")
    print(f"Total internal-to-api mappings: {len(scheme_loader._INTERNAL_TO_API_ID)}")
    
    production_internal_ids = set(scheme_loader._INTERNAL_TO_API_ID.keys())
    
    # 2. Get vector store scheme IDs
    if not os.path.exists(STORE_PATH):
        print(f"Vector store not found at {STORE_PATH}")
        sys.exit(1)
        
    from pathlib import Path
    store = VectorStore.load(Path(STORE_PATH))
    
    rag_scheme_ids = set(chunk.scheme_id for chunk in store.chunks)
    
    print(f"Total production schemes: {len(production_internal_ids)}")
    print(f"Total schemes in RAG: {len(rag_scheme_ids)}")
    
    missing = production_internal_ids - rag_scheme_ids
    orphaned = rag_scheme_ids - production_internal_ids
    
    print("\n--- COVERAGE RESULTS ---")
    print(f"Missing from RAG (0 is goal): {len(missing)}")
    if missing:
        for m in missing:
            print(f"  - {m}")
            
    print(f"Orphaned in RAG (0 is goal): {len(orphaned)}")
    if orphaned:
        for o in orphaned:
            print(f"  - {o}")
            
    if len(missing) == 0 and len(orphaned) == 0:
        print("\n✅ RAG COVERAGE VERIFIED: 100% matched.")
    else:
        print("\n❌ RAG COVERAGE FAILED.")
        sys.exit(1)

if __name__ == "__main__":
    main()
