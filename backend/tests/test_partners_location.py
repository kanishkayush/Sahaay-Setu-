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


def test_all_partners_works_without_location():
    res = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "language": "en", "radiusKm": 1000},
    )
    assert res.status_code == 200
    body = res.json()
    assert "searchedFrom" in body
    assert body["searchedFrom"] is None
    assert len(body["items"]) >= 1


def test_all_partners_accepting_only_zero_is_success_not_error():
    res = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": True, "language": "en", "radiusKm": 1000},
    )
    assert res.status_code == 200
    body = res.json()
    assert "searchedFrom" in body
    assert body["searchedFrom"] is None
    assert isinstance(body.get("items"), list)
    for p in body["items"]:
        assert (p.get("eligibility") or {}).get("status") == "ACCEPTING"


def test_only_accepting_false_does_not_drop_unknown_partners():
    accepting = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": True, "language": "en", "radiusKm": 1000},
    ).json()["items"]
    all_items = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "language": "en", "radiusKm": 1000},
    ).json()["items"]
    assert len(all_items) >= len(accepting)
    assert any((p.get("eligibility") or {}).get("status") == "UNKNOWN" for p in all_items)


def test_nearby_is_not_the_national_catalogue():
    nearby = client.post(
        "/v1/partners/search",
        json={"location": JAIPUR, "radiusKm": 25, "onlyAccepting": False, "allPartners": False},
    ).json()["items"]
    catalogue = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "radiusKm": 1000},
    ).json()["items"]
    assert len(catalogue) > len(nearby)


def test_profile_coordinates_persist_through_put_get():
    headers = {"X-User-Id": "validation-loc-user"}
    put = client.put(
        "/v1/profile",
        headers=headers,
        json={
            "address": {
                "pinCode": "302017",
                "city": "Jaipur",
                "district": "Jaipur",
                "state": "Rajasthan",
                "coordinates": JAIPUR,
            }
        },
    )
    assert put.status_code == 200
    got = client.get("/v1/profile", headers=headers)
    assert got.status_code == 200
    coords = ((got.json().get("address") or {}).get("coordinates") or {})
    address = got.json().get("address") or {}
    assert coords.get("latitude") == JAIPUR["latitude"]
    assert coords.get("longitude") == JAIPUR["longitude"]
    assert address.get("pinCode") == "302017"
    assert address.get("district") == "Jaipur"
    assert address.get("state") == "Rajasthan"
    nearby = client.post(
        "/v1/partners/search",
        json={"location": coords, "radiusKm": 50, "onlyAccepting": False, "allPartners": False},
    )
    assert nearby.status_code == 200
    body = nearby.json()
    assert body.get("searchedFrom") == JAIPUR
    for p in body["items"]:
        assert p.get("distanceKm") is not None
        assert p["distanceKm"] <= 50


def test_profile_string_coordinates_persist_through_put_get():
    headers = {"X-User-Id": "string-coord-user"}
    put = client.put(
        "/v1/profile",
        headers=headers,
        json={
            "address": {
                "pinCode": "302017",
                "city": "Jaipur",
                "state": "Rajasthan",
                "coordinates": {"latitude": "26.9124", "longitude": "75.7873"},
            }
        },
    )
    assert put.status_code == 200
    got = client.get("/v1/profile", headers=headers)
    assert got.status_code == 200
    coords = ((got.json().get("address") or {}).get("coordinates") or {})
    assert float(coords.get("latitude")) == 26.9124
    assert float(coords.get("longitude")) == 75.7873
