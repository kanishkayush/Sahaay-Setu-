"""
app/api/scheme_loader.py
────────────────────────
Single function: load the api presentation block from each scheme JSON.

The eligibility engine reads `parameters` from the same files.
The API mapper reads `api` from the same files.
data/schemes/*.json is the only source of truth for both.

The loaded dict is cached at module import time — the files are read once
and held in memory for the process lifetime. This is intentional: the data
changes only when a scheme parameter is updated, which requires a redeploy.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_DATA_DIR = Path(__file__).parent.parent.parent / "data" / "schemes"

# scheme_id → api presentation dict (SchemeSchema shape)
_CACHE: dict[str, dict[str, Any]] = {}
_INTERNAL_TO_API_ID: dict[str, str] = {}


import re

def normalize_category(cat: str) -> str:
    if not cat:
        return "UNKNOWN"
    return re.sub(r'[\s\-]+', '_', cat.strip()).upper()

def _load_all() -> dict[str, dict[str, Any]]:
    global _INTERNAL_TO_API_ID
    result: dict[str, dict[str, Any]] = {}
    mapping: dict[str, str] = {}
    for path in _DATA_DIR.glob("*.json"):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        api_block: dict[str, Any] | None = data.get("api")
        internal_id: str = data.get("scheme_id", "")
        if api_block:
            # Normalize category
            if "category" in api_block:
                api_block["category"] = normalize_category(api_block["category"])

            # Frontend Zod contract expects recommendationCategory as array of strings.
            # Legacy JSON files may store it as a bare string; coerce here so the
            # ContractViolationError never fires in the client.
            rc = api_block.get("recommendationCategory")
            if isinstance(rc, str):
                api_block["recommendationCategory"] = [rc] if rc else []
            elif rc is None:
                api_block["recommendationCategory"] = []
                
            # Use api.id as the canonical key — this is what the frontend uses
            # for /schemes/{id} navigation. The top-level scheme_id is used by
            # the eligibility engine only.
            api_id: str = api_block.get("id", "")
            if api_id:
                result[api_id] = api_block
                if internal_id:
                    mapping[internal_id] = api_id
    
    _INTERNAL_TO_API_ID = mapping
    return result



def get_scheme_catalogue() -> dict[str, dict[str, Any]]:
    """
    Returns {api_id: api_block} for every scheme that has an `api` block.
    Cached after first call.
    """
    global _CACHE
    if not _CACHE:
        _CACHE = _load_all()
    return _CACHE


def get_scheme(scheme_id: str) -> dict[str, Any] | None:
    return get_scheme_catalogue().get(scheme_id)


def get_scheme_by_internal_id(internal_id: str) -> dict[str, Any] | None:
    # Ensure cache is loaded
    get_scheme_catalogue()
    api_id = _INTERNAL_TO_API_ID.get(internal_id)
    if api_id:
        return get_scheme(api_id)
    return None


def reset_cache() -> None:
    """Force-reload scheme data. Used in tests and hot-reload scenarios."""
    global _CACHE
    _CACHE = _load_all()
