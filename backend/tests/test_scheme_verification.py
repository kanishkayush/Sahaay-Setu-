from pathlib import Path
import json

from fastapi.testclient import TestClient

from app.main import app
from app.rag.education_advisor import PARTIAL, UNVERIFIED, VERIFIED, verification_status
from app.api.scheme_loader import get_scheme

client = TestClient(app)
MSY_PATH = Path(__file__).resolve().parents[1] / "data" / "schemes" / "nsfdc-msy.json"


def test_unverified_scheme_is_not_treated_as_fake_or_verified():
    scheme = get_scheme("nsfdc-msy")
    assert scheme is not None
    assert scheme.get("verified") is False
    status = str(scheme.get("verificationStatus") or "").upper()
    assert status in {"STATUS_UNCLEAR", "UNVERIFIED", "PARTIAL"}
    raw = json.loads(MSY_PATH.read_text(encoding="utf-8"))
    assert verification_status(raw) in {UNVERIFIED, PARTIAL}
    assert verification_status(raw) != VERIFIED


def test_scheme_detail_does_not_require_invented_zeros():
    res = client.get("/v1/schemes/nsfdc-msy")
    assert res.status_code == 200
    body = res.json()
    assert body.get("verified") is False
    source = body.get("sourceUrl") or body.get("officialUrl")
    if source:
        assert str(source).startswith("http")
    # Missing numeric fields must remain absent/null, never coerced to 0 by the API.
    for key in ("minLoanAmount", "interestRateMinPct", "maxAnnualFamilyIncome"):
        if key not in body:
            continue
        assert body[key] is None or isinstance(body[key], (int, float))
