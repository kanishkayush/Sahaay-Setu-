from typing import Protocol, List, Dict, Any, Optional

class PartnerRepositoryProtocol(Protocol):
    def search_nearby(
        self,
        latitude: float,
        longitude: float,
        radius_km: float,
        scheme_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Finds channel partners within radius_km, optionally supporting scheme_id."""
        ...

    def search_by_pincode_with_expansion(
        self,
        pincode: str,
        scheme_id: Optional[str] = None,
        max_radius_km: float = 1000.0,
        initial_radius_km: float = 10.0
    ) -> List[Dict[str, Any]]:
        """Finds channel partners using pincode with expanding radius search."""
        ...

    def get_by_id(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific channel partner by its ID."""
        ...
