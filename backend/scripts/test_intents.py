import requests
import json

queries = [
    # Education
    "I need a study loan.",
    "I need an education loan.",
    "I need a loan for my college.",
    "I need a loan for my BTech.",
    "I need financing for my degree.",
    "I need money for my MBA.",
    "I want a student loan.",
    "I need a loan for higher education.",
    "I need financial help for my studies.",
    "I need a loan to pay my college fees.",
    "I need a loan for my college BTech degree.",
    
    # Business
    "I want to start a dairy business.",
    "I want a loan to start a new business.",
    "I already run a dairy business.",
    "I need financing for my handicraft business.",
    "I need money to expand my existing business.",
    
    # Ambiguous
    "I need a loan.",
    "I need financial help.",
    "Which loan is available for me?",
    "I need funding."
]

url = "http://localhost:8000/v1/assistant/query"
headers = {
    "Content-Type": "application/json",
    "x-user-id": "test-user-123"
}

results = []

import uuid

for q in queries:
    session_id = str(uuid.uuid4())
    payload = {
        "query": q,
        "sessionId": session_id,
        "responseLanguage": "en",
        "guideMe": True
    }
    try:
        resp = requests.post(url, json=payload, headers=headers)
        data = resp.json()
        
        answer = data.get("answer", "")
        expected_field = data.get("expectedField", "")
        
        print(f"Q: {q}")
        print(f"A: {answer}")
        print(f"Field: {expected_field}")
        print("-" * 40)
    except Exception as e:
        print(f"Error on {q}: {e}")
