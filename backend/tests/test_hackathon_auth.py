import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_login_valid_1():
    res = client.post("/v1/auth/login", json={"mobile": "9876543210"})
    assert res.status_code == 200
    data = res.json()
    assert data["token"]
    assert data["userId"]
    assert data["phoneNumber"] == "+919876543210"

def test_login_valid_2():
    res = client.post("/v1/auth/login", json={"mobile": "+919876543210"})
    assert res.status_code == 200
    assert res.json()["phoneNumber"] == "+919876543210"

def test_login_valid_3():
    res = client.post("/v1/auth/login", json={"mobile": "09876543210"})
    assert res.status_code == 200
    assert res.json()["phoneNumber"] == "+919876543210"

def test_login_invalid_1():
    res = client.post("/v1/auth/login", json={"mobile": "123"})
    assert res.status_code == 400

def test_login_invalid_2():
    res = client.post("/v1/auth/login", json={"mobile": ""})
    assert res.status_code == 400

def test_login_invalid_3():
    res = client.post("/v1/auth/login", json={"mobile": "987654321"})
    assert res.status_code == 400

def test_login_invalid_4():
    res = client.post("/v1/auth/login", json={"mobile": "98765432101"})
    assert res.status_code == 400

def test_login_invalid_5():
    res = client.post("/v1/auth/login", json={"mobile": "98765abc10"})
    assert res.status_code == 400
