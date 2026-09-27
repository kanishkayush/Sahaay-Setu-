import json
import os
import uuid
from pathlib import Path

FRONTEND_SCHEMES_FILE = "/Users/kanishkshahi/SIH_2026_RAG/frontend/schemes.json"
BACKEND_SCHEMES_DIR = "/Users/kanishkshahi/SIH_2026_RAG/backend/data/schemes"

def main():
    if not os.path.exists(FRONTEND_SCHEMES_FILE):
        print("Frontend schemes file not found.")
        return

    with open(FRONTEND_SCHEMES_FILE, "r") as f:
        data = json.load(f)
    
    items = data.get("items", [])
    
    for item in items:
        # Some are already nsfdc-*, skip those as they might be the 8 ones
        if item.get("id", "").startswith("nsfdc-"):
            continue
            
        scheme_id = str(item.get("id", uuid.uuid4()))
        
        # Create backend schema format
        backend_schema = {
            "scheme_id": scheme_id,
            "api": {
                "id": scheme_id,
                "code": item.get("code", "UNKNOWN"),
                "name": item.get("name", {}),
                "shortDescription": item.get("shortDescription", {}),
                "officialCategory": item.get("officialCategory", "OTHER"),
                "recommendationCategory": item.get("recommendationCategory", ["OTHER"]),
                "channelPartnerRequired": item.get("channelPartnerRequired", False),
                "minLoanAmount": item.get("minLoanAmount", 10000),
                "maxLoanAmount": item.get("maxLoanAmount", 100000),
                "fundingSharePct": item.get("fundingSharePct", 0.9),
                "interestRateMinPct": item.get("interestRateMinPct", 6.5),
                "interestRateMaxPct": item.get("interestRateMaxPct", 8.0),
                "maxTenureMonths": item.get("maxTenureMonths", 36),
                "moratoriumMinMonths": item.get("moratoriumMinMonths", 3),
                "moratoriumMaxMonths": item.get("moratoriumMaxMonths", 6),
                "maxAnnualFamilyIncome": item.get("maxAnnualFamilyIncome", 500000),
                "eligibleGender": item.get("eligibleGender", "ANY"),
                "eligibilityRules": item.get("eligibilityRules", []),
                "documentsRequired": item.get("documentsRequired", []),
                "channelPartnerTypes": item.get("channelPartnerTypes", []),
                "citations": item.get("citations", []),
                "verified": item.get("verified", False),
                "lastUpdatedAt": item.get("lastUpdatedAt", "2026-09-08T00:00:00.000Z"),
                "officialUrl": item.get("officialUrl", "")
            }
        }
        
        file_path = os.path.join(BACKEND_SCHEMES_DIR, f"{scheme_id}.json")
        with open(file_path, "w", encoding="utf-8") as out:
            json.dump(backend_schema, out, indent=2, ensure_ascii=False)
            
    print(f"Ingested {len(items)} schemes.")
    
    # Generate mock variants to reach 120 total
    current_files = len(list(Path(BACKEND_SCHEMES_DIR).glob("*.json")))
    target = 120
    to_generate = target - current_files
    
    if to_generate > 0:
        base_item = backend_schema # use last one
        for i in range(to_generate):
            new_id = f"mock-scheme-{i}"
            mock_schema = json.loads(json.dumps(base_item))
            mock_schema["scheme_id"] = new_id
            mock_schema["api"]["id"] = new_id
            mock_schema["api"]["code"] = f"MOCK-{i}"
            mock_schema["api"]["name"]["en"] = f"Mock Scheme {i} (Generated to test scale)"
            
            file_path = os.path.join(BACKEND_SCHEMES_DIR, f"{new_id}.json")
            with open(file_path, "w", encoding="utf-8") as out:
                json.dump(mock_schema, out, indent=2, ensure_ascii=False)
                
        print(f"Generated {to_generate} mock schemes to reach {target}.")

if __name__ == "__main__":
    main()
