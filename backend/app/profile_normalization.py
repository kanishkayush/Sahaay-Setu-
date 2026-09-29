"""Canonical profile normalization for RAG, recommendations, and partners.

Unknown booleans stay None. They are never coerced to False.
"""

from __future__ import annotations

from typing import Any, Optional

from app.recommendation_engine import RelevanceQuery


PROJECT_TYPE_TO_DOMAIN: dict[str, Optional[str]] = {
    "AGRICULTURE": "AGRICULTURE",
    "ANIMAL_HUSBANDRY": "AGRICULTURE",
    "ARTISAN_CRAFT": "BUSINESS",
    "RETAIL_SHOP": "BUSINESS",
    "SERVICES": "BUSINESS",
    "SMALL_MANUFACTURING": "BUSINESS",
    "TRANSPORT_VEHICLE": "BUSINESS",
    "EDUCATION": "EDUCATION",
    "OTHER": None,
}


def tri_bool(value: Any) -> Optional[bool]:
    """Preserve explicit True/False; treat missing as unknown."""
    if value is True or value is False:
        return value
    return None


def relevance_from_project_type(
    project_type: Optional[str],
    amount_inr: Optional[float] = None,
    activity: Optional[str] = None,
    gender: Optional[str] = None,
) -> RelevanceQuery:
    domain = PROJECT_TYPE_TO_DOMAIN.get(project_type or "", None)
    mapped_activity = activity
    if mapped_activity is None and project_type == "ANIMAL_HUSBANDRY":
        mapped_activity = "LIVESTOCK"
    return RelevanceQuery(
        assistance_type="LOAN",
        domain=domain,
        activity=mapped_activity,
        amount_inr=amount_inr,
        gender=gender,
    )


def is_valid_coordinates(lat: Any, lon: Any) -> bool:
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return False
    if lat_f != lat_f or lon_f != lon_f:  # NaN
        return False
    if abs(lat_f) > 90 or abs(lon_f) > 180:
        return False
    if lat_f == 0.0 and lon_f == 0.0:
        return False
    return True


def normalize_profile_location(profile: Any) -> Optional[dict[str, float]]:
    """Canonical stored location is address.coordinates."""
    if not isinstance(profile, dict):
        return None
    address = profile.get("address") if isinstance(profile.get("address"), dict) else {}
    coords = address.get("coordinates") if isinstance(address, dict) else None
    if isinstance(coords, dict):
        lat, lon = coords.get("latitude"), coords.get("longitude")
        if is_valid_coordinates(lat, lon):
            return {"latitude": float(lat), "longitude": float(lon)}
    nested = profile.get("location") if isinstance(profile.get("location"), dict) else None
    if isinstance(nested, dict) and is_valid_coordinates(nested.get("latitude"), nested.get("longitude")):
        return {"latitude": float(nested["latitude"]), "longitude": float(nested["longitude"])}
    if is_valid_coordinates(profile.get("latitude"), profile.get("longitude")):
        return {"latitude": float(profile["latitude"]), "longitude": float(profile["longitude"])}
    return None
