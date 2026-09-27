import os
from pathlib import Path
from sentence_transformers import SentenceTransformer

def main():
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    # Download to the project directory so Render includes it in the final image
    cache_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "rag", "model_cache")
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading {model_name} to {cache_dir}...")
    # This triggers the download and caches it
    SentenceTransformer(model_name, cache_folder=cache_dir)
    print("Download complete.")

if __name__ == "__main__":
    main()
