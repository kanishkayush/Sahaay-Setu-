"""Validated lifecycle and provenance helpers for scheme records."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any
import json


class SchemeStatus(str, Enum):
    CURRENT_ACTIVE = "CURRENT_ACTIVE"
    CURRENT_BUT_LIMITED = "CURRENT_BUT_LIMITED"
    HISTORICAL = "HISTORICAL"
    REPLACED = "REPLACED"
    UNCLEAR_STATUS = "UNCLEAR_STATUS"


ACTIVE_STATUSES = {
    SchemeStatus.CURRENT_ACTIVE.value,
    SchemeStatus.CURRENT_BUT_LIMITED.value,
}


def lifecycle_status(scheme: dict[str, Any]) -> str:
    return str(scheme.get("status") or SchemeStatus.UNCLEAR_STATUS.value).upper()


def is_current(scheme: dict[str, Any]) -> bool:
    return lifecycle_status(scheme) in ACTIVE_STATUSES


def is_recommendable(scheme: dict[str, Any]) -> bool:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    return bool(
        is_current(scheme)
        and scheme.get("verified") is True
        and api.get("verified") is not False
        and scheme.get("catalogue_visible", True)
    )


def provenance_issues(scheme: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    provenance = scheme.get("provenance")
    if not isinstance(provenance, list) or not provenance:
        issues.append("missing_provenance")
    else:
        for source in provenance:
            if not isinstance(source, dict):
                issues.append("invalid_provenance")
                continue
            for key in ("source_url", "source_title", "retrieved_at"):
                if not source.get(key):
                    issues.append(f"provenance_missing_{key}")
    if not scheme.get("status"):
        issues.append("missing_status")
    return sorted(set(issues))


def validate_catalogue(schemes_dir: Path) -> list[dict[str, Any]]:
    """Return structured validation failures; never mutates catalogue files."""
    seen_ids: set[str] = set()
    failures: list[dict[str, Any]] = []
    for path in sorted(schemes_dir.glob("*.json")):
        with path.open(encoding="utf-8") as handle:
            scheme = json.load(handle)
        sid = str(scheme.get("scheme_id") or "")
        issues = provenance_issues(scheme)
        if not sid:
            issues.append("missing_scheme_id")
        elif sid in seen_ids:
            issues.append("duplicate_scheme_id")
        seen_ids.add(sid)
        if lifecycle_status(scheme) not in {status.value for status in SchemeStatus}:
            issues.append("invalid_status")
        if is_recommendable(scheme) and str(scheme.get("source_url") or "").lower() in {
            "",
            "unknown",
        }:
            issues.append("recommendable_missing_source")
        if issues:
            failures.append({"scheme_id": sid or path.stem, "issues": sorted(set(issues))})
    return failures
