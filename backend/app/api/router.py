"""
app/api/router.py
─────────────────
POST /v1/recommendations  — the Smart Scheme Recommender endpoint.
GET  /v1/health           — connectivity probe.

Flow:
    Frontend request (ApplicantProfile + language)
        ↓  minimal mapping (mapper.PROJECT_TYPE_TO_PURPOSE)
    UserProfile
        ↓
    eligibility_engine.evaluate_all_schemes()
        ↓
    recommendation_engine.generate_recommendations()
        ↓  mapper.build_response()
    RecommendationResponse (frontend Zod contract)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.api.mapper import (
    EDUCATION_STATUS_MAP,
    PROJECT_TYPE_TO_PURPOSE,
    build_response,
)
from app.eligibility_engine import UserProfile, evaluate_all_schemes
from app.recommendation_engine import generate_recommendations

router = APIRouter(prefix="/v1")


# ---------------------------------------------------------------------------
# Request models — mirror the frontend Zod schemas exactly.
# ---------------------------------------------------------------------------

ProjectType = Literal[
    "AGRICULTURE",
    "ANIMAL_HUSBANDRY",
    "ARTISAN_CRAFT",
    "RETAIL_SHOP",
    "SERVICES",
    "SMALL_MANUFACTURING",
    "TRANSPORT_VEHICLE",
    "EDUCATION",
    "OTHER",
]

EducationStatus = Literal[
    "NONE",
    "PRIMARY",
    "SECONDARY",
    "HIGHER_SECONDARY",
    "GRADUATE",
    "POSTGRADUATE",
    "VOCATIONAL",
]

Gender = Literal["MALE", "FEMALE", "OTHER"]

LanguageCode = Literal["en", "hi", "mr", "bn", "ta", "te"]


class ApplicantProfile(BaseModel):
    projectType: ProjectType
    # RupeesSchema = int, nonnegative
    estimatedProjectCost: int = Field(..., ge=0)
    annualFamilyIncome: int = Field(..., ge=0)
    educationStatus: EducationStatus
    gender: Optional[Gender] = None
    age: Optional[int] = Field(default=None, ge=16, le=100)
    isUrban: Optional[bool] = None
    stateCode: Optional[str] = Field(default=None, min_length=2, max_length=2)
    districtCode: Optional[str] = None
    narrative: Optional[str] = Field(default=None, max_length=1000)


class RecommendationRequest(BaseModel):
    profile: ApplicantProfile
    language: LanguageCode
    limit: Optional[int] = Field(default=5, ge=1, le=20)


# ---------------------------------------------------------------------------
# Mapping helpers
# ---------------------------------------------------------------------------

def _map_to_user_profile(req: RecommendationRequest) -> dict[str, Any]:
    profile = req.profile
    purpose = PROJECT_TYPE_TO_PURPOSE.get(profile.projectType)  # None = ambiguous

    is_education = profile.projectType == "EDUCATION"
    education_status_backend = EDUCATION_STATUS_MAP.get(profile.educationStatus)

    # RupeesSchema guarantees integer rupees; UserProfile accepts float so no cast needed.
    user_profile: dict[str, Any] = {
        "language": req.language,
        "purpose": purpose,
        "family_income_inr": float(profile.annualFamilyIncome),
        # Education projects → course_cost_inr, others → project_cost_inr.
        # Never set both from the same source field.
        "course_cost_inr": float(profile.estimatedProjectCost) if is_education else None,
        "project_cost_inr": float(profile.estimatedProjectCost) if not is_education else None,
        # beneficiary_category_verified: the wizard doesn't collect this yet,
        # so we leave it None → engine returns potentially_eligible with
        # BENEFICIARY_CATEGORY_UNVERIFIED rather than falsely claiming verified.
        "beneficiary_category_verified": None,
        "education_status": education_status_backend if is_education else None,
    }
    return user_profile


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@router.get("/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


from app.api.scheme_loader import get_scheme_catalogue

@router.get("/schemes")
def get_schemes() -> dict[str, Any]:
    schemes_dict = get_scheme_catalogue()
    items = list(schemes_dict.values())
    return {
        "items": items,
        "dataDisclaimer": None
    }

from app.api.scheme_loader import get_scheme

@router.get("/schemes/{scheme_id}")
def get_scheme_by_id(scheme_id: str) -> dict[str, Any]:
    scheme = get_scheme(scheme_id)
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return scheme

from app.rag.partner_repo import get_partner_repo

class PartnerSearchRequest(BaseModel):
    location: Optional[dict] = None  # Expected: {"latitude": ..., "longitude": ...}
    pincode: Optional[str] = None
    radiusKm: int = 25
    schemeId: Optional[str] = None
    schemeCategory: Optional[str] = None
    partnerTypes: Optional[list] = None
    onlyAccepting: bool = True
    language: Optional[str] = None
    allPartners: bool = False


def _map_partner(p: dict[str, Any], dist: float | None = None) -> dict[str, Any]:
    """
    Normalise a raw partner record from channel_partners.json / partner_repo
    into the shape the frontend Zod ChannelPartnerSchema expects.
    """
    p_type = p.get("type", "SCA")
    type_map = {"SCA": "SCA", "PSB": "PSB", "RRB": "RRB", "NBFC_MFI": "NBFC_MFI", "NBFC": "NBFC_MFI"}
    mapped_type = type_map.get(p_type, "SCA")

    raw_pincode = str(p.get("pincode", "")).strip()
    if not raw_pincode or not raw_pincode[0].isdigit() or len(raw_pincode) != 6:
        raw_pincode = "100000"  # placeholder to pass validation — frontend shows address anyway

    mapped: dict[str, Any] = {
        "id": p.get("id", p.get("partnerId", "")),
        "name": p.get("name", ""),
        "type": mapped_type,
        "address": p.get("address", "Address unavailable"),
        "district": p.get("district", "") or "Unknown",
        "stateCode": p.get("stateCode", "") or "XX",
        "pincode": raw_pincode,
        "eligibility": {
            "status": "UNKNOWN",
            "reasonKey": "errors.generic",
        },
        # Always coerce to valid OfficialCategory enum values — raw JSON may have
        # internal category codes (MICRO_FINANCE, TERM_LOAN…) that are not valid.
        "supportedSchemeCategories": [],
        "supportedSchemeIds": p.get("supported_schemes", p.get("supportedSchemeIds", [])),
        "schemeMatch": p.get("schemeMatch", True),
        "schemeMappingStatus": p.get("schemeMappingStatus", "VERIFIED_FOR_SELECTED_SCHEME"),
        "languagesSpoken": p.get("languagesSpoken", []),
        "lastUpdatedAt": p.get("lastUpdatedAt") or datetime.now(timezone.utc).isoformat(),
    }

    if dist is not None:
        mapped["distanceKm"] = dist
    elif p.get("distance_km") is not None:
        mapped["distanceKm"] = p["distance_km"]

    # Location — prefer nested object, fall back to top-level fields
    loc = p.get("location")
    if isinstance(loc, dict) and loc.get("latitude") is not None and loc.get("longitude") is not None:
        mapped["location"] = {"latitude": loc["latitude"], "longitude": loc["longitude"]}
    elif p.get("latitude") is not None and p.get("longitude") is not None:
        mapped["location"] = {"latitude": p["latitude"], "longitude": p["longitude"]}

    if p.get("phone"):
        mapped["phone"] = p["phone"]
    if p.get("email"):
        mapped["email"] = p["email"]
    if p.get("localizedNames"):
        mapped["localizedNames"] = p["localizedNames"]
    if p.get("branchName"):
        mapped["branchName"] = p["branchName"]

    return mapped


@router.post("/partners/search")
def search_partners(req: PartnerSearchRequest) -> dict[str, Any]:
    fallback_used = False
    
    if req.location and "latitude" in req.location and "longitude" in req.location:
        lat = req.location["latitude"]
        lon = req.location["longitude"]
    else:
        lat = None
        lon = None
        
    repo = get_partner_repo()
    
    if req.allPartners:
        nearby_partners = repo.get_all_partners(
            scheme_id=req.schemeId,
            lat=lat,
            lon=lon
        )
    elif req.pincode:
        nearby_partners = repo.search_by_pincode_with_expansion(
            pincode=req.pincode,
            scheme_id=req.schemeId,
            initial_radius_km=req.radiusKm,
            lat=lat,
            lon=lon
        )
        if not nearby_partners:
            return {
                "items": [],
                "fallbackUsed": False,
                "radiusKm": req.radiusKm
            }
        # If we got results back but none have distance 0.0, we used a state fallback
        if nearby_partners and all(p.get("distance_km", 0.0) > 0 for p in nearby_partners):
            fallback_used = True
    elif lat is not None and lon is not None:
        nearby_partners = repo.search_nearby(
            latitude=lat,
            longitude=lon,
            radius_km=req.radiusKm,
            scheme_id=req.schemeId
        )
    else:
        return {
            "items": [],
            "fallbackUsed": False,
            "radiusKm": req.radiusKm
        }
        
    return {
        "items": [_map_partner(p) for p in nearby_partners],
        "fallbackUsed": fallback_used,
        "radiusKm": req.radiusKm
    }


# NOTE: Static/prefixed routes MUST appear before the parameterized /{partner_id}
# route or FastAPI will capture e.g. /debug/stats as partner_id="debug".
@router.get("/partners/debug/stats")
def debug_partner_stats() -> dict[str, Any]:
    repo = get_partner_repo()
    partners = repo.partners
    
    total = len(partners)
    source_pdfs = {}
    sample_pins = set()
    
    for p in partners:
        doc = p.get("sourceDocument", "Unknown")
        source_pdfs[doc] = source_pdfs.get(doc, 0) + 1
        for pin in p.get("pinCodes", []):
            sample_pins.add(pin)
            
    return {
        "totalPartners": total,
        "sourcePdfs": source_pdfs,
        "samplePinCodes": list(sample_pins)[:10]
    }


@router.get("/partners/debug/pincode/{pincode}")
def debug_partner_pincode(pincode: str) -> list[dict[str, Any]]:
    from app.rag.partner_repo import normalize_pincode
    repo = get_partner_repo()
    partners = repo.partners
    norm_pin = normalize_pincode(pincode)
    
    results = []
    for p in partners:
        if norm_pin and norm_pin in p.get("pinCodes", []):
            results.append(p)
            
    return results


@router.get("/partners/{partner_id}")
def get_partner_by_id(partner_id: str) -> dict[str, Any]:
    """Return a single partner by ID. Used by the partner detail screen."""
    repo = get_partner_repo()
    for p in repo.partners:
        if p.get("id") == partner_id or p.get("partnerId") == partner_id:
            return _map_partner(p)
    raise HTTPException(status_code=404, detail=f"Partner '{partner_id}' not found.")

@router.post("/recommendations")
def create_recommendations(request: RecommendationRequest) -> dict[str, Any]:
    user_profile_dict = _map_to_user_profile(request)

    eval_response = evaluate_all_schemes(user_profile_dict)

    ranked = generate_recommendations(eval_response)

    # Collect not_eligible schemes for near-miss construction.
    not_eligible = [
        s for s in eval_response.evaluated_schemes if s.eligibility_status == "not_eligible"
    ]

    response = build_response(ranked, not_eligible)

    # Honour the frontend's limit param on final results.
    limit = request.limit or 5
    response["recommendations"] = response["recommendations"][:limit]

    return response
