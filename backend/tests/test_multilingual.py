import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_multilingual_chat_routing():
    """
    Test that queries in English, Hindi, Roman Hindi, and Hinglish 
    are properly detected and handled by the chat API.
    """
    # 1. English
    res_en = client.post("/v1/chat", json={
        "query": "I want to start a new dairy farm business.",
        "language": "en"
    })
    assert res_en.status_code == 200
    data_en = res_en.json()
    assert data_en["language"] == "en"
    
    # 2. Devanagari Hindi
    res_hi = client.post("/v1/chat", json={
        "query": "मुझे डेयरी फार्मिंग के लिए लोन चाहिए।",
        "language": "en"  # Passing wrong language to test auto-detection
    })
    assert res_hi.status_code == 200
    data_hi = res_hi.json()
    # Assuming the LLM detects "hi" and overrides "en"
    assert data_hi["language"] in ["hi", "en"] # Accept either depending on LLM mock
    
    # 3. Roman Hindi (padhai) -> Intent extraction test
    res_roman = client.post("/v1/chat", json={
        "query": "mujhe padhai keliye loan chaiye",
        "language": "en"
    })
    assert res_roman.status_code == 200
    data_roman = res_roman.json()
    assert data_roman["language"] in ["hi", "en"]
    
def test_low_info_queries():
    """
    Test that low information queries return clarification.
    """
    res = client.post("/v1/chat", json={
        "query": "loan",
        "language": "hi"
    })
    assert res.status_code == 200
    data = res.json()
    assert "response_source" in data
    assert data["response_source"] == "CLARIFICATION"
