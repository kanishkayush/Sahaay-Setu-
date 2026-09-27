import json
import os
import glob

frontend_schemes_path = "/Users/kanishkshahi/SIH_2026_RAG/frontend/schemes.json"
backend_schemes_dir = "/Users/kanishkshahi/SIH_2026_RAG/backend/data/schemes"

with open(frontend_schemes_path, "r", encoding="utf-8") as f:
    data = json.load(f)

items = data.get("items", [])
count = 0

for item in items:
    scheme_id = item.get("id")
    if scheme_id.startswith("nsfdc-"):
        # We already have authoritative detailed JSON files for these in the backend.
        continue
    
    file_path = os.path.join(backend_schemes_dir, f"{scheme_id}.json")
    with open(file_path, "w", encoding="utf-8") as out:
        json.dump(item, out, indent=2, ensure_ascii=False)
    count += 1

print(f"Total items in frontend/schemes.json: {len(items)}")
print(f"Extracted {count} non-nsfdc items to {backend_schemes_dir}.")

# Let's count existing nsfdc items
nsfdc_files = glob.glob(os.path.join(backend_schemes_dir, "nsfdc-*.json"))
print(f"Existing NSFDC detailed files: {len(nsfdc_files)}")
print(f"Total production schemes: {count + len(nsfdc_files)}")
