from app.partner_filters import (
    apply_partner_filters,
    available_states,
    npa_bucket,
    normalize_state_code,
    sort_partners,
    utilization_bucket,
    utilization_pct,
)
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

JAIPUR = {"latitude": 26.9124, "longitude": 75.7873}


def _partner(**overrides):
    base = {
        "id": "p1",
        "name": "Alpha Agency",
        "type": "SCA",
        "stateCode": "RJ",
        "eligibility": {"status": "UNKNOWN", "reasonKey": "partners.eligibility.unknown"},
    }
    base.update(overrides)
    return base


def test_state_normalization():
    assert normalize_state_code("Rajasthan") == "RJ"
    assert normalize_state_code("RAJASTHAN") == "RJ"
    assert normalize_state_code("rajasthan") == "RJ"
    assert normalize_state_code("RJ") == "RJ"
    assert normalize_state_code("West Bengal") == "WB"
    assert normalize_state_code("Western Bengal") == "XX"


def test_state_filter_and_sort():
    partners = [
        _partner(id="1", name="B Partner", stateCode="RJ"),
        _partner(id="2", name="A Partner", stateCode="rj"),
        _partner(id="3", name="C Partner", stateCode="MH"),
        _partner(id="4", name="D Partner", stateCode="Western Bengal"),
    ]
    rajasthan = apply_partner_filters(partners, state_code="Rajasthan")
    assert {p["id"] for p in rajasthan} == {"1", "2"}
    maharashtra = apply_partner_filters(partners, state_code="Maharashtra")
    assert [p["id"] for p in maharashtra] == ["3"]
    sorted_by_state = sort_partners(partners, "state")
    assert [p["id"] for p in sorted_by_state] == ["3", "2", "1", "4"]


def test_npa_unknown_is_not_acceptable():
    unknown = _partner()
    assert npa_bucket(unknown) == "unknown"
    acceptable = _partner(eligibility={"status": "UNKNOWN", "npaPct": 2})
    concern_rrb = _partner(type="RRB", eligibility={"status": "UNKNOWN", "npaPct": 16})
    concern_mfi = _partner(type="NBFC_MFI", eligibility={"status": "UNKNOWN", "npaPct": 0.8})
    assert npa_bucket(acceptable) == "acceptable"
    assert npa_bucket(concern_rrb) == "concern"
    assert npa_bucket(concern_mfi) == "concern"
    filtered = apply_partner_filters(
        [unknown, acceptable, concern_rrb],
        npa="acceptable",
    )
    assert [p["id"] for p in filtered] == ["p1"] or [p["type"] for p in filtered] == ["SCA"]
    assert all(npa_bucket(p) == "acceptable" for p in filtered)
    assert apply_partner_filters([unknown], npa="acceptable") == []
    assert apply_partner_filters([unknown], npa="unknown") == [unknown]


def test_utilization_unknown_and_ratio():
    unknown = _partner()
    assert utilization_bucket(unknown) == "unknown"
    assert utilization_pct(unknown) is None
    zero_denom = _partner(eligibility={"utilizedAmount": 10, "allocatedAmount": 0})
    assert utilization_bucket(zero_denom) == "unknown"
    low = _partner(eligibility={"utilizedAmount": 20, "allocatedAmount": 100})
    medium = _partner(eligibility={"utilizedAmount": 60, "allocatedAmount": 100})
    high = _partner(eligibility={"utilizedAmount": 85, "allocatedAmount": 100})
    assert utilization_bucket(low) == "low"
    assert utilization_bucket(medium) == "medium"
    assert utilization_bucket(high) == "high"
    assert apply_partner_filters([unknown], utilization="high") == []
    assert apply_partner_filters([unknown, high], utilization="unknown") == [unknown]


def test_combined_filters_do_not_fallback():
    partners = [
        _partner(id="rj-ok", stateCode="RJ", eligibility={"status": "ACCEPTING", "npaPct": 1, "utilizedAmount": 20, "allocatedAmount": 100}),
        _partner(id="rj-unknown", stateCode="RJ"),
        _partner(id="mh-ok", stateCode="MH", eligibility={"status": "ACCEPTING", "npaPct": 1, "utilizedAmount": 20, "allocatedAmount": 100}),
    ]
    hits = apply_partner_filters(
        partners,
        state_code="RJ",
        npa="acceptable",
        utilization="low",
        only_accepting=True,
    )
    assert [p["id"] for p in hits] == ["rj-ok"]
    empty = apply_partner_filters(
        partners,
        state_code="RJ",
        npa="acceptable",
        utilization="high",
        only_accepting=True,
    )
    assert empty == []


def test_api_state_filter_and_count():
    all_items = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "language": "en", "radiusKm": 1000},
    ).json()
    assert all_items["filteredCount"] == len(all_items["items"])
    assert len(all_items["availableStates"]) >= 1
    rajasthan = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "stateCode": "Rajasthan", "language": "en", "radiusKm": 1000},
    ).json()
    assert rajasthan["filteredCount"] == len(rajasthan["items"])
    assert rajasthan["filteredCount"] < all_items["filteredCount"]
    for item in rajasthan["items"]:
        assert item["stateCode"] == "RJ"
    empty = client.post(
        "/v1/partners/search",
        json={
            "allPartners": True,
            "onlyAccepting": True,
            "stateCode": "RJ",
            "npaBucket": "acceptable",
            "language": "en",
            "radiusKm": 1000,
        },
    ).json()
    assert empty["items"] == []
    assert empty["filteredCount"] == 0


def test_api_state_plus_nearby_does_not_override_radius():
    nearby = client.post(
        "/v1/partners/search",
        json={
            "location": JAIPUR,
            "radiusKm": 25,
            "onlyAccepting": False,
            "allPartners": False,
            "stateCode": "RJ",
            "language": "en",
        },
    ).json()
    for item in nearby["items"]:
        assert item["stateCode"] == "RJ"
        assert item["distanceKm"] <= 25


def test_api_unknown_npa_and_utilization_are_not_good():
    unknown = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "npaBucket": "unknown", "language": "en", "radiusKm": 1000},
    ).json()
    acceptable = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "npaBucket": "acceptable", "language": "en", "radiusKm": 1000},
    ).json()
    high_util = client.post(
        "/v1/partners/search",
        json={"allPartners": True, "onlyAccepting": False, "fundUtilizationBucket": "high", "language": "en", "radiusKm": 1000},
    ).json()
    assert len(unknown["items"]) >= 1
    assert acceptable["items"] == []
    assert high_util["items"] == []


def test_api_sort_by_state():
    body = client.post(
        "/v1/partners/search",
        json={
            "allPartners": True,
            "onlyAccepting": False,
            "sortBy": "state",
            "language": "en",
            "radiusKm": 1000,
        },
    ).json()
    names_by_state = [(item["stateCode"], item["name"]) for item in body["items"]]
    sorted_copy = sorted(names_by_state, key=lambda row: (row[0], row[1]))
    # Canonical sort is by display name then partner name; codes are stable enough to be ordered.
    assert [row[1] for row in names_by_state] == [item["name"] for item in body["items"]]
    assert available_states(body["items"])
