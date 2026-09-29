"""Partner catalogue filters based on fields that actually exist.

The live channel_partners.json records:
- stateCode (ISO 3166-2:IN suffix, or XX when unknown)
- eligibility.status (currently UNKNOWN for every partner)
- eligibility.npaPct / unutilisedLimit / overdueAmount — optional, currently absent
- eligibility.utilizedAmount / allocatedAmount — not present in the live feed

Filters never invent NPA or utilisation figures. Missing values are UNKNOWN.
Accepting status, NPA, and fund utilisation are independent axes.
"""

from __future__ import annotations

from typing import Any, Iterable, Literal

NpaBucket = Literal["all", "unknown", "acceptable", "concern"]
UtilBucket = Literal["all", "unknown", "low", "medium", "high"]
SortKey = Literal["distance", "name", "type", "state"]

# NSFDC allocation-of-funds utilisation release threshold (COMMON_RELEASE_NORMS).
NSFDC_UTILISATION_RELEASE_PCT = 80.0
# Split of the range *below* that documented 80% threshold, used only when a
# utilisation ratio can actually be computed from utilizedAmount/allocatedAmount.
UTILISATION_LOW_MEDIUM_SPLIT_PCT = 50.0

# Canonical names for codes present in channel_partners.json (plus common aliases).
IN_STATE_NAMES: dict[str, str] = {
    "AP": "Andhra Pradesh",
    "AR": "Arunachal Pradesh",
    "AS": "Assam",
    "BR": "Bihar",
    "CG": "Chhattisgarh",
    "DL": "Delhi",
    "GJ": "Gujarat",
    "HP": "Himachal Pradesh",
    "HR": "Haryana",
    "JH": "Jharkhand",
    "JK": "Jammu and Kashmir",
    "KA": "Karnataka",
    "MH": "Maharashtra",
    "MN": "Manipur",
    "MP": "Madhya Pradesh",
    "MZ": "Mizoram",
    "OD": "Odisha",
    "PB": "Punjab",
    "RJ": "Rajasthan",
    "TN": "Tamil Nadu",
    "TS": "Telangana",
    "UP": "Uttar Pradesh",
    "WB": "West Bengal",
    "XX": "Unknown / not coded",
}

_NAME_TO_CODE = {name.casefold(): code for code, name in IN_STATE_NAMES.items()}


def normalize_state_code(raw: str | None) -> str:
    """Map RJ / rajasthan / Rajasthan to RJ. Unknown names are not aliased together."""
    if raw is None:
        return "XX"
    text = str(raw).strip()
    if not text:
        return "XX"
    upper = text.upper()
    if len(upper) == 2 and upper in IN_STATE_NAMES:
        return upper
    mapped = _NAME_TO_CODE.get(text.casefold())
    if mapped:
        return mapped
    return "XX"


def state_display_name(code: str) -> str:
    return IN_STATE_NAMES.get(normalize_state_code(code), IN_STATE_NAMES["XX"])


def _eligibility(partner: dict[str, Any]) -> dict[str, Any]:
    elig = partner.get("eligibility")
    return elig if isinstance(elig, dict) else {}


def _distance_km(partner: dict[str, Any]) -> float | None:
    for key in ("distanceKm", "distance_km"):
        value = partner.get(key)
        if value is None:
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
    return None


def npa_bucket(partner: dict[str, Any]) -> str:
    """Classify from published npaPct only. Missing → unknown.

    UNKNOWN eligibility status is not 'acceptable'. Thresholds come from NSFDC
    prudential norms and are applied only when a real npaPct figure exists.
    """
    elig = _eligibility(partner)
    npa = elig.get("npaPct")
    if npa is None:
        return "unknown"
    try:
        value = float(npa)
    except (TypeError, ValueError):
        return "unknown"
    partner_type = str(partner.get("type") or "")
    if partner_type == "RRB":
        return "concern" if value >= 15 else "acceptable"
    if partner_type in {"NBFC_MFI", "NBFC"}:
        return "concern" if value >= 0.5 else "acceptable"
    if elig.get("reasonKey") == "partners.eligibility.highNpa":
        return "concern"
    return "acceptable"


def utilization_pct(partner: dict[str, Any]) -> float | None:
    elig = _eligibility(partner)
    utilised = elig.get("utilizedAmount")
    allocated = elig.get("allocatedAmount")
    if utilised is None or allocated is None:
        return None
    try:
        denom = float(allocated)
        numer = float(utilised)
    except (TypeError, ValueError):
        return None
    if denom <= 0:
        return None
    return (numer / denom) * 100


def utilization_bucket(partner: dict[str, Any]) -> str:
    """Low/medium/high only when both amount fields are valid. Otherwise unknown.

    unutilisedLimit alone cannot produce a percentage, so it stays unknown.
    """
    pct = utilization_pct(partner)
    if pct is None:
        return "unknown"
    if pct >= NSFDC_UTILISATION_RELEASE_PCT:
        return "high"
    if pct >= UTILISATION_LOW_MEDIUM_SPLIT_PCT:
        return "medium"
    return "low"


def apply_partner_filters(
    partners: Iterable[dict[str, Any]],
    *,
    state_code: str | None = None,
    npa: NpaBucket = "all",
    utilization: UtilBucket = "all",
    only_accepting: bool | None = None,
) -> list[dict[str, Any]]:
    wanted_state = None
    raw_state = str(state_code).strip() if state_code is not None else ""
    if raw_state and raw_state.upper() != "ALL":
        wanted_state = normalize_state_code(raw_state)
    out: list[dict[str, Any]] = []
    for partner in partners:
        if wanted_state and normalize_state_code(partner.get("stateCode")) != wanted_state:
            continue
        if npa != "all" and npa_bucket(partner) != npa:
            continue
        if utilization != "all" and utilization_bucket(partner) != utilization:
            continue
        if only_accepting:
            status = str(_eligibility(partner).get("status") or "UNKNOWN")
            if status != "ACCEPTING":
                continue
        out.append(partner)
    return out


def sort_partners(
    partners: list[dict[str, Any]],
    sort_by: SortKey = "name",
    *,
    location_available: bool = True,
) -> list[dict[str, Any]]:
    items = list(partners)
    if sort_by == "distance" and location_available:
        items.sort(
            key=lambda p: (
                _distance_km(p) is None,
                _distance_km(p) if _distance_km(p) is not None else 999999,
                p.get("name") or "",
            )
        )
        return items
    if sort_by == "type":
        items.sort(key=lambda p: ((p.get("type") or ""), (p.get("name") or "")))
        return items
    if sort_by == "state":
        items.sort(
            key=lambda p: (
                state_display_name(str(p.get("stateCode") or "XX")),
                p.get("name") or "",
            )
        )
        return items
    items.sort(key=lambda p: (p.get("name") or ""))
    return items


def available_states(partners: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: dict[str, int] = {}
    for partner in partners:
        code = normalize_state_code(partner.get("stateCode"))
        seen[code] = seen.get(code, 0) + 1
    return [
        {"code": code, "name": state_display_name(code), "count": seen[code]}
        for code in sorted(seen, key=lambda c: state_display_name(c))
    ]
