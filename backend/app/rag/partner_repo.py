import json
import math
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.core.interfaces.partner_repo import PartnerRepositoryProtocol

def normalize_pincode(value: Any) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip()
    if value.endswith(".0"):
        value = value[:-2]
    digits = "".join(char for char in value if char.isdigit())
    if len(digits) == 6:
        return digits
    return None

def normalize_scheme_id(value: Any) -> Optional[str]:
    if not value:
        return None
    val = str(value).strip().upper()
    val = re.sub(r'[^A-Z0-9]+', '_', val)
    # Special mappings for known schemes
    if "TERM" in val or "TL" in val:
        return "TERM_LOAN"
    if "MICRO" in val or "MFS" in val:
        return "MICRO_FINANCE"
    if "EDU" in val or "ELS" in val:
        return "EDUCATION_LOAN"
    if "ENTREPRENEUR" in val:
        return "ENTREPRENEURSHIP"
    if "MAHILA" in val or "SAMRIDDHI" in val or "MSY" in val:
        return "MAHILA_SAMRIDDHI_YOJANA"
    if "VOCATIONAL" in val or "VETLS" in val:
        return "VOCATIONAL_TRAINING"
    return val

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in kilometers between two points on Earth."""
    R = 6371.0  # Earth radius in kilometers

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * \
        math.sin(delta_lambda / 2.0) ** 2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class JsonPartnerRepository(PartnerRepositoryProtocol):
    def __init__(self, data_path: str = "data/channel_partners.json"):
        self.data_path = Path(data_path)
        self.partners = self._load_data()

    def _load_data(self) -> List[Dict[str, Any]]:
        if not self.data_path.exists():
            return []
        with open(self.data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        # Normalize the dataset in-memory
        for p in data:
            raw_pins = p.get("pinCodes", [])
            norm_pins = []
            for pin in raw_pins:
                norm = normalize_pincode(pin)
                if norm:
                    norm_pins.append(norm)
            p["pinCodes"] = norm_pins
            
            raw_schemes = p.get("schemes", [])
            norm_schemes = []
            for s in raw_schemes:
                ns = normalize_scheme_id(s)
                if ns and ns not in norm_schemes:
                    norm_schemes.append(ns)
            p["supported_schemes"] = norm_schemes
            
        return data

    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        scheme_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = []
        
        for partner in self.partners:
            if scheme_id and scheme_id not in partner.get("supported_schemes", []):
                continue
                
            p_lat = partner.get("latitude")
            p_lon = partner.get("longitude")
            
            if p_lat is None or p_lon is None:
                continue
                
            distance = haversine_distance(latitude, longitude, p_lat, p_lon)
            
            if distance <= radius_km:
                # Add distance field for the response
                partner_with_dist = partner.copy()
                partner_with_dist["distance_km"] = round(distance, 2)
                results.append(partner_with_dist)
                
        # Sort by distance
        results.sort(key=lambda x: x["distance_km"])
        return results

    def search_by_pincode_with_expansion(
        self,
        pincode: str,
        scheme_id: Optional[str] = None,
        max_radius_km: float = 100.0,
        initial_radius_km: float = 25.0,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        results = []
        
        # Normalize requested PIN and Scheme
        norm_pincode = normalize_pincode(pincode)
        norm_req_scheme = normalize_scheme_id(scheme_id)

        if not norm_pincode:
            return []

        # Step 0: Find state/district for this pincode from any partner that has it
        target_state = ""
        target_district = ""
        for partner in self.partners:
            if norm_pincode == partner.get("pincode"):
                if partner.get("state") and partner.get("state") != "Unknown":
                    target_state = partner.get("state").lower()
                if partner.get("district"):
                    target_district = partner.get("district").lower()
                if target_state and target_district:
                    break

        exact_matches = []
        district_matches = []
        state_matches = []

        for partner in self.partners:
            partner_with_dist = partner.copy()
            
            # Check scheme support
            scheme_match = True
            mapping_status = "VERIFIED_FOR_SELECTED_SCHEME"
            if norm_req_scheme:
                partner_schemes = partner.get("supported_schemes", [])
                if partner_schemes and norm_req_scheme not in partner_schemes:
                    scheme_match = False
                    mapping_status = "NOT_VERIFIED_FOR_SELECTED_SCHEME"
            
            partner_with_dist["schemeMatch"] = scheme_match
            partner_with_dist["schemeMappingStatus"] = mapping_status
            
            # Distance computation if user GPS is available and partner has GPS
            dist_km = None
            if lat is not None and lon is not None:
                p_loc = partner.get("location") or {}
                p_lat = p_loc.get("latitude") or partner.get("latitude")
                p_lon = p_loc.get("longitude") or partner.get("longitude")
                if p_lat is not None and p_lon is not None:
                    dist_km = round(haversine_distance(lat, lon, float(p_lat), float(p_lon)), 2)
                    partner_with_dist["distance_km"] = dist_km
            
            p_pincode = str(partner.get("pincode", ""))
            p_state = str(partner.get("state", "")).lower()
            p_district = str(partner.get("district", "")).lower()
            
            # Match tiers
            is_exact = (norm_pincode == p_pincode)
            is_district = (target_district and p_district == target_district)
            is_state = (target_state and p_state == target_state)
            
            if is_exact:
                exact_matches.append(partner_with_dist)
            elif is_district:
                district_matches.append(partner_with_dist)
            elif is_state:
                state_matches.append(partner_with_dist)

        # Sort each tier by distance (if available) then scheme match
        def sort_key(x):
            d = x.get("distance_km")
            return (not x["schemeMatch"], d if d is not None else 999999)

        exact_matches.sort(key=sort_key)
        district_matches.sort(key=sort_key)
        state_matches.sort(key=sort_key)
        
        final_results = []
        seen_ids = set()
        
        for tier in [exact_matches, district_matches, state_matches]:
            for p in tier:
                pid = p.get("id") or p.get("partnerId")
                if pid not in seen_ids:
                    final_results.append(p)
                    seen_ids.add(pid)
                    
        return final_results

    def get_all_partners(
        self,
        scheme_id: Optional[str] = None,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        norm_req_scheme = normalize_scheme_id(scheme_id)
        results = []
        
        for partner in self.partners:
            partner_with_dist = partner.copy()
            
            # Check scheme support
            scheme_match = True
            mapping_status = "VERIFIED_FOR_SELECTED_SCHEME"
            if norm_req_scheme:
                partner_schemes = partner.get("supported_schemes", [])
                if partner_schemes and norm_req_scheme not in partner_schemes:
                    scheme_match = False
                    mapping_status = "NOT_VERIFIED_FOR_SELECTED_SCHEME"
            
            partner_with_dist["schemeMatch"] = scheme_match
            partner_with_dist["schemeMappingStatus"] = mapping_status
            
            # Distance computation if user GPS is available and partner has GPS
            if lat is not None and lon is not None:
                p_loc = partner.get("location") or {}
                p_lat = p_loc.get("latitude") or partner.get("latitude")
                p_lon = p_loc.get("longitude") or partner.get("longitude")
                if p_lat is not None and p_lon is not None:
                    dist_km = round(haversine_distance(lat, lon, float(p_lat), float(p_lon)), 2)
                    partner_with_dist["distance_km"] = dist_km
            
            results.append(partner_with_dist)
            
        return results

    def get_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        for partner in self.partners:
            if partner.get("partner_id") == partner_id:
                return partner
        return None

# Global instance for use by endpoints
# Resolve path relative to the app execution directory (usually backend root)
import os
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
default_path = os.path.join(base_dir, "data", "channel_partners.json")

repo = JsonPartnerRepository(default_path)

def get_partner_repo() -> PartnerRepositoryProtocol:
    return repo
