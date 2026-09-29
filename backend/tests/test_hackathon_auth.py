from fastapi.testclient import TestClient

from app.auth_mobile import normalize_indian_mobile
from app.main import app

client = TestClient(app)


def test_normalize_accepts_valid_indian_numbers():
    assert normalize_indian_mobile("9876543210") == "9876543210"
    assert normalize_indian_mobile("9123456789") == "9123456789"
    assert normalize_indian_mobile("8123456789") == "8123456789"
    assert normalize_indian_mobile("7012345678") == "7012345678"
    assert normalize_indian_mobile("9999999999") == "9999999999"


def test_normalize_strips_prefix_and_separators():
    assert normalize_indian_mobile("+91 9876543210") == "9876543210"
    assert normalize_indian_mobile("+91-9876543210") == "9876543210"
    assert normalize_indian_mobile("98765 43210") == "9876543210"
    assert normalize_indian_mobile("09876543210") == "9876543210"


def test_normalize_rejects_invalid():
    for raw in ["1234567890", "5123456789", "987654321", "98765432101", "abcdefghij", "", "   ", "99999999"]:
        assert normalize_indian_mobile(raw) is None


def test_login_valid_numbers_create_session():
    for mobile in ["9876543210", "9123456789", "8123456789", "7012345678"]:
        res = client.post("/v1/auth/login", json={"mobile": mobile})
        assert res.status_code == 200
        data = res.json()
        assert data["token"]
        assert data["userId"] == data["token"]
        assert data["phoneNumber"] == f"+91{mobile}"


def test_login_same_mobile_is_stable_identity():
    first = client.post("/v1/auth/login", json={"mobile": "9876543210"}).json()
    second = client.post("/v1/auth/login", json={"mobile": "+91 9876543210"}).json()
    assert first["userId"] == second["userId"]
    assert first["token"] == second["token"]


def test_login_rejects_invalid_numbers():
    for mobile in ["1234567890", "5123456789", "987654321", "98765432101", "abcdefghij", "99999999"]:
        res = client.post("/v1/auth/login", json={"mobile": mobile})
        assert res.status_code == 400


def test_demo_ten_nines_is_a_normal_valid_number_not_an_allowlist():
    res = client.post("/v1/auth/login", json={"mobile": "9999999999"})
    assert res.status_code == 200
    other = client.post("/v1/auth/login", json={"mobile": "9876543210"})
    assert other.status_code == 200
    assert res.json()["userId"] != other.json()["userId"]
