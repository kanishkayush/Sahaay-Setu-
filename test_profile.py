import requests

BASE_URL = "http://localhost:8001/v1"

# 1. Request OTP
res = requests.post(f"{BASE_URL}/auth/send-otp", json={"phoneNumber": "9999999999"})
print("Login:", res.json())

# 2. Verify OTP
res = requests.post(f"{BASE_URL}/auth/verify-otp", json={"phoneNumber": "9999999999", "otp": "123456"})
token = res.json()["token"]
headers = {"Authorization": f"Bearer {token}"}
print("Verified, got token")

# 3. Update Profile
payload = {
    "fullName": "Kanishk Shahi",
    "phoneNumber": "9999999999",
    "email": "kanishk@example.com",
    "dateOfBirth": "1990-01-01",
    "address": {
        "pinCode": "110001",
        "state": "Delhi",
        "district": "New Delhi",
        "city": "New Delhi",
        "addressLine1": "Connaught Place"
    },
    "educationLevel": "Post Graduate",
    "occupation": "Software Engineer",
    "eligibility": {
        "annualFamilyIncome": 1200000,
        "scEligibilityStatus": True
    },
    "business": {
        "existingBusiness": True,
        "businessActivity": "IT Services"
    }
}
res = requests.put(f"{BASE_URL}/profile", json=payload, headers=headers)
print("PUT Status:", res.status_code)

# 4. Fetch Profile
res = requests.get(f"{BASE_URL}/profile", headers=headers)
print("GET Status:", res.status_code)
data = res.json()
print("GET Response:", data)

assert data["fullName"] == "Kanishk Shahi"
assert data["eligibility"]["annualFamilyIncome"] == 1200000
print("SUCCESS: Persistence verified.")
