import json, glob, os

for path in glob.glob("backend/data/schemes/*.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if "api" not in data:
        # Wrap it
        scheme_id = data.get("id") or data.get("scheme_id")
        new_data = {
            "scheme_id": scheme_id,
            "api": data
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(new_data, f, indent=2, ensure_ascii=False)
        print(f"Fixed {os.path.basename(path)}")

