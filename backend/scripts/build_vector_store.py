import json
import os
from pathlib import Path

# Fix python path
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.rag.chunker import Chunk
from app.rag.vector_store import build_store
from app.rag.embeddings import embed

BACKEND_SCHEMES_DIR = "/Users/kanishkshahi/SIH_2026_RAG/backend/data/schemes"
STORE_PATH = Path("/Users/kanishkshahi/SIH_2026_RAG/backend/data/rag/vector_store.npz")

def main():
    chunks = []
    
    for filename in os.listdir(BACKEND_SCHEMES_DIR):
        if not filename.endswith(".json"):
            continue
            
        path = os.path.join(BACKEND_SCHEMES_DIR, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        scheme_id = data.get("scheme_id", "")
        api_block = data.get("api", {})
        
        name_en = api_block.get("name", {}).get("en", "")
        desc_en = api_block.get("shortDescription", {}).get("en", "")
        cat = api_block.get("officialCategory", "")
        
        if not name_en:
            continue
            
        # Create an overview chunk
        chunk = Chunk(
            chunk_id=f"{scheme_id}__overview__0",
            scheme_id=scheme_id,
            scheme_name=name_en,
            section="overview",
            language="en",
            source_id=scheme_id,
            source_priority="1",
            financial_terms_status="AVAILABLE",
            last_verified="2026-09-08",
            text=f"Scheme Name: {name_en}\nDescription: {desc_en}\nCategory: {cat}"
        )
        chunks.append(chunk)
        
        # Create a financial terms chunk
        min_loan = api_block.get("minLoanAmount", "")
        max_loan = api_block.get("maxLoanAmount", "")
        int_min = api_block.get("interestRateMinPct", "")
        int_max = api_block.get("interestRateMaxPct", "")
        
        if max_loan:
            fin_chunk = Chunk(
                chunk_id=f"{scheme_id}__financial_terms__0",
                scheme_id=scheme_id,
                scheme_name=name_en,
                section="financial_terms",
                language="en",
                source_id=scheme_id,
                source_priority="1",
                financial_terms_status="AVAILABLE",
                last_verified="2026-09-08",
                text=f"Financial Terms for {name_en}: Loan Amount is {min_loan} to {max_loan}. Interest Rate is {int_min}% to {int_max}%."
            )
            chunks.append(fin_chunk)

    print(f"Total chunks created: {len(chunks)}")
    
    # We must use SAARTHI_MOCK_EMBEDDING=1 for testing if huggingface isn't available, but let's try standard embed
    os.environ["SAARTHI_MOCK_EMBEDDING"] = "1"
    
    print("Building vector store...")
    store = build_store(chunks, embed)
    store.save(STORE_PATH)
    print(f"Vector store saved to {STORE_PATH}")

if __name__ == "__main__":
    main()
