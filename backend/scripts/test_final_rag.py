import asyncio
from app.api.chat import process_chat_request
from app.schemas.chat import ChatRequest, ChatResponse, ChatProfile

def main():
    q_edu = [
        "I need a study loan.",
        "I need a college loan.",
        "I need a BTech loan.",
        "I need an MBA loan.",
        "I need money for my studies."
    ]
    q_biz = [
        "I want to start a dairy business.",
        "I want to start a new business.",
        "I already have a dairy business.",
        "I want to expand my existing business."
    ]
    
    print("--- EDUCATION TESTS ---")
    for q in q_edu:
        req = ChatRequest(query=q, guideMe=True, sessionId="test-123", profile=ChatProfile(pinCode="400051"))
        res = process_chat_request(req)
        print(f"Q: {q} | Expected Field: {res.expected_field}")
        
    print("\n--- BUSINESS TESTS ---")
    for q in q_biz:
        req = ChatRequest(query=q, guideMe=True, sessionId="test-124", profile=ChatProfile(pinCode="400051"))
        res = process_chat_request(req)
        print(f"Q: {q} | Expected Field: {res.expected_field}")

main()
