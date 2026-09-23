import json
import os

keys_to_add = {
    "distanceUnavailable": "Distance unavailable",
    "locationUnavailable": "Location unavailable",
    "selectPartner": "Select Partner",
    "getDirections": "Get Directions",
    "viewOnMap": "View on Map",
    "locationInfoUnavailable": "Location information unavailable",
    "tryAgain": "Try again",
    "nearby": "Nearby",
    "allPartners": "All Partners",
    "distanceLabel": "Distance",
    "nameLabel": "Name",
    "typeLabel": "Partner Type",
    "noPartnersFound": "No partners found",
    "enableLocation": "Enable location",
    "noVerifiedMapPartners": "No verified partner locations are available on the map."
}

locales_dir = "frontend/src/i18n/locales"
locales = ["en", "hi", "mr", "bn", "ta", "te"]

translations = {
    "hi": {
        "distanceUnavailable": "दूरी अनुपलब्ध",
        "locationUnavailable": "स्थान अनुपलब्ध",
        "selectPartner": "साझेदार चुनें",
        "getDirections": "दिशा-निर्देश प्राप्त करें",
        "viewOnMap": "मानचित्र पर देखें",
        "locationInfoUnavailable": "स्थान की जानकारी अनुपलब्ध है",
        "tryAgain": "पुनः प्रयास करें",
        "nearby": "आस-पास",
        "allPartners": "सभी साझेदार",
        "distanceLabel": "दूरी",
        "nameLabel": "नाम",
        "typeLabel": "साझेदार का प्रकार",
        "noPartnersFound": "कोई साझेदार नहीं मिला",
        "enableLocation": "स्थान सक्षम करें",
        "noVerifiedMapPartners": "मानचित्र पर कोई सत्यापित साझेदार स्थान उपलब्ध नहीं है।"
    }
}

for loc in locales:
    filepath = os.path.join(locales_dir, f"{loc}.json")
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if "partners" not in data:
            data["partners"] = {}
            
        for k, v in keys_to_add.items():
            if k not in data["partners"]:
                if loc == "en":
                    data["partners"][k] = v
                elif loc == "hi" and k in translations["hi"]:
                    data["partners"][k] = translations["hi"][k]
                else:
                    data["partners"][k] = v # fallback for others, can be replaced by users later

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

print("Done")
