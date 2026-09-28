"""Nearby partner search uses real coordinates and does not dump the national list."""

from app.rag.partner_repo import haversine_distance, partner_coordinates, JsonPartnerRepository
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

JAIPUR = {"latitude": 26.9124, "longitude": 75.7873}


def test_partner_coordinates_reject_null_island():
    assert partner_coordinates({"latitude": 0, "longitude": 0}) is None
    assert partner_coordinates({"location": {"latitude": 17.385, "longitude": 78.4867}}) == (17.385, 78.4867)


def test_nearby_without_location_returns_empty():
    res = client.post(
        "/v1/partners/search",
        json={"radiusKm": 100, "onlyAccepting": True, "allPartners": False, "language": "en"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["items"] == []
    assert body.get("fallbackUsed") is False


def test_nearby_radius_filters_by_haversine():
    res = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 25,
            "onlyAccepting": False,
            "allPartners": False,
            "language": "en",
        },
    )
    assert res.status_code == 200
    items = res.json()["items"]
    for p in items:
        loc = p.get("location")
        assert loc is not None
        dist = haversine_distance(JAIPUR["latitude"], JAIPUR["longitude"], loc["latitude"], loc["longitude"])
        assert dist <= 25 + 0.05
        assert p.get("distanceKm") is not None


def test_nearby_excludes_partners_without_coordinates():
    res = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 100,
            "onlyAccepting": False,
            "allPartners": False,
            "language": "en",
        },
    )
    assert res.status_code == 200
    for p in res.json()["items"]:
        assert p.get("location")
        assert p.get("distanceKm") is not None
        assert p["distanceKm"] <= 100


def test_all_partners_is_not_radius_limited():
    nearby = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 25,
            "onlyAccepting": False,
            "allPartners": False,
            "language": "en",
        },
    ).json()["items"]
    all_partners = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 25,
            "onlyAccepting": False,
            "allPartners": True,
            "language": "en",
        },
    ).json()["items"]
    assert len(all_partners) >= len(nearby)


def test_only_accepting_excludes_unknown_status():
    res = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 1000,
            "onlyAccepting": True,
            "allPartners": True,
            "language": "en",
        },
    )
    assert res.status_code == 200
    for p in res.json()["items"]:
        assert (p.get("eligibility") or {}).get("status") == "ACCEPTING"


def test_search_nearby_uses_nested_location():
    repo = JsonPartnerRepository()
    sample = next((p for p in repo.partners if partner_coordinates(p)), None)
    assert sample is not None
    lat, lon = partner_coordinates(sample)
    hits = repo.search_nearby(lat, lon, radius_km=1)
    assert hits
    assert hits[0].get("distance_km") is not None
    assert hits[0]["distance_km"] <= 1
