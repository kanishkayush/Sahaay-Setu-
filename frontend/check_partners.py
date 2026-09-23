import json

with open("../backend/data/channel_partners.json") as f:
    data = json.load(f)

for item in data:
    if "email" in item and item["email"] == "":
        print(f"Partner {item['id']} has empty email")
    if "pincode" in item and not isinstance(item["pincode"], str):
        print(f"Partner {item['id']} has invalid pincode type")
    if "pincode" in item and len(str(item["pincode"])) != 6:
        print(f"Partner {item['id']} has invalid pincode length")
