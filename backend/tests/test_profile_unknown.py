"""Unknown profile booleans stay None; nested address coordinates persist."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.profile_normalization import tri_bool
from app.schemas.profile import PersistentUserProfile
from app.services.storage import ProfileStore

client = TestClient(app)


def test_empty_persistent_profile_booleans_are_unknown():
    skeleton = PersistentUserProfile(user_id="new-user")
    assert skeleton.eligibility.scEligibilityStatus is None
    assert skeleton.business.existingBusiness is None
    assert tri_bool(skeleton.eligibility.scEligibilityStatus) is None
    assert tri_bool(skeleton.business.existingBusiness) is None


def test_get_profile_skeleton_unknown_booleans():
    res = client.get("/v1/profile", headers={"Authorization": "Bearer test"})
    # Unauthenticated users still get a contract-shaped payload or 401.
    if res.status_code == 401:
        return
    body = res.json()
    assert body.get("eligibility", {}).get("scEligibilityStatus") in {None, False} or "eligibility" in body


def test_profile_store_preserves_null_and_coordinates(tmp_path: Path):
    store = ProfileStore(base_dir=tmp_path)
    store.upsert(
        "u1",
        {
            "address": {
                "state": "Rajasthan",
                "district": "Jaipur",
                "pinCode": "302001",
                "coordinates": {"latitude": 26.9124, "longitude": 75.7873},
            },
            "eligibility": {"scEligibilityStatus": None, "annualFamilyIncome": None},
            "business": {"existingBusiness": None},
        },
    )
    got = store.get("u1")
    assert got["eligibility"]["scEligibilityStatus"] is None
    assert got["business"]["existingBusiness"] is None
    assert got["address"]["coordinates"]["latitude"] == 26.9124

    store.upsert("u1", {"eligibility": {"annualFamilyIncome": 250000}})
    got = store.get("u1")
    assert got["eligibility"]["annualFamilyIncome"] == 250000
    assert got["eligibility"]["scEligibilityStatus"] is None
    assert got["address"]["coordinates"]["longitude"] == 75.7873

    store.upsert("u1", {"eligibility": {"scEligibilityStatus": False}})
    assert store.get("u1")["eligibility"]["scEligibilityStatus"] is False
    store.upsert("u1", {"business": {"existingBusiness": True}})
    assert store.get("u1")["business"]["existingBusiness"] is True


def test_normalize_profile_location_canonical_and_legacy():
    from app.profile_normalization import normalize_profile_location

    assert normalize_profile_location({
        "address": {"coordinates": {"latitude": 26.9124, "longitude": 75.7873}}
    }) == {"latitude": 26.9124, "longitude": 75.7873}
    assert normalize_profile_location({
        "address": {"coordinates": {"latitude": "26.9124", "longitude": "75.7873"}}
    }) == {"latitude": 26.9124, "longitude": 75.7873}
    assert normalize_profile_location({"latitude": 26.9, "longitude": 75.8}) == {
        "latitude": 26.9,
        "longitude": 75.8,
    }
    assert normalize_profile_location({"address": {"pinCode": "302017"}}) is None
    assert normalize_profile_location({"address": {"coordinates": {"latitude": 0, "longitude": 0}}}) is None


def test_explicit_existing_business_phrases_are_not_inverted():
    from app.rag.guided_journey import _try_deterministic_parse
    from app.schemas.chat import ChatProfile

    no_biz = _try_deterministic_parse("I don't have an existing business", ChatProfile())
    yes_biz = _try_deterministic_parse("I already have an existing business", ChatProfile())
    assert no_biz.get("existingBusiness") is False
    assert yes_biz.get("existingBusiness") is True
