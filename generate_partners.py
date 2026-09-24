import json
import random

with open('/Users/kanishkshahi/SIH_2026_RAG/backend/data/channel_partners.json', 'r') as f:
    partners = json.load(f)

# Base template for a partner
template = {
    "supportedSchemeCategories": [
        "MICRO_FINANCE",
        "TERM_LOAN",
        "EDUCATION_LOAN"
    ],
    "supportedSchemeIds": [],
    "schemeMatch": True,
    "schemeMappingStatus": "VERIFIED_FOR_SELECTED_SCHEME",
    "eligibility": {
        "status": "UNKNOWN",
        "reasonKey": "partners.eligibility.unknown",
        "lastAssessedAt": "2026-09-07T00:00:00.000Z"
    },
    "languagesSpoken": ["en"],
    "lastUpdatedAt": "2026-09-07T00:00:00.000Z"
}

cities = [
    {"city": "Mumbai", "stateCode": "MH", "pincode": "400051", "lat": 19.076, "lon": 72.8777},
    {"city": "Pune", "stateCode": "MH", "pincode": "411001", "lat": 18.5204, "lon": 73.8567},
    {"city": "Nagpur", "stateCode": "MH", "pincode": "440001", "lat": 21.1458, "lon": 79.0882},
    {"city": "Delhi", "stateCode": "DL", "pincode": "110002", "lat": 28.6139, "lon": 77.2090},
    {"city": "Chennai", "stateCode": "TN", "pincode": "600035", "lat": 13.0827, "lon": 80.2707},
    {"city": "Kolkata", "stateCode": "WB", "pincode": "700091", "lat": 22.5726, "lon": 88.3639},
    {"city": "Bengaluru", "stateCode": "KA", "pincode": "560001", "lat": 12.9716, "lon": 77.5946},
    {"city": "Hyderabad", "stateCode": "TS", "pincode": "500001", "lat": 17.3850, "lon": 78.4867},
    {"city": "Ahmedabad", "stateCode": "GJ", "pincode": "380001", "lat": 23.0225, "lon": 72.5714},
    {"city": "Jaipur", "stateCode": "RJ", "pincode": "302001", "lat": 26.9124, "lon": 75.7873}
]

types = ["BANK", "NBFC_MFI", "SCA"]
names = ["Global Finance", "Apex Trust", "Regional Cooperative", "State Dev Corp", "Urban Microfinance", "Rural Loan Assoc", "Pioneer Lending"]

new_partners = []
for i in range(70):
    city = random.choice(cities)
    ptype = random.choice(types)
    name = f"{random.choice(names)} {city['city']} Branch {i}"
    
    partner = template.copy()
    partner["id"] = f"partner-{i+6}"
    partner["name"] = name
    partner["localizedNames"] = {}
    partner["type"] = ptype
    partner["address"] = city["city"]
    partner["district"] = city["city"]
    partner["stateCode"] = city["stateCode"]
    partner["pincode"] = city["pincode"]
    partner["location"] = {
        "latitude": city["lat"] + random.uniform(-0.1, 0.1),
        "longitude": city["lon"] + random.uniform(-0.1, 0.1)
    }
    new_partners.append(partner)

partners.extend(new_partners)

with open('/Users/kanishkshahi/SIH_2026_RAG/backend/data/channel_partners.json', 'w') as f:
    json.dump(partners, f, indent=2)

print(f"Generated 70 new partners. Total: {len(partners)}")
