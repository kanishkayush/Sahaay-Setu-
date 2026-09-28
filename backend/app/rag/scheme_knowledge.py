"""
Build semantically meaningful RAG chunks from authoritative scheme JSON.

Does not invent facts. Missing fields are omitted or marked unknown.
Every chunk keeps scheme_id and organization metadata.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Optional

from app.rag.chunker import Chunk

SCHEMES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "schemes"
PLACEHOLDER_MARKERS = (
    "currently being fetched",
    "official scheme details are currently",
)


def _loc(value: Any) -> dict[str, str]:
    if isinstance(value, dict):
        return {str(k): str(v) for k, v in value.items() if v not in (None, "")}
    if isinstance(value, str) and value.strip():
        return {"en": value.strip()}
    return {}


def _join_langs(parts: dict[str, str]) -> str:
    en = parts.get("en", "")
    hi = parts.get("hi", "")
    if en and hi and hi != en:
        return f"{en}\n{hi}"
    return en or hi or next(iter(parts.values()), "")


def _is_placeholder(text: str) -> bool:
    low = (text or "").lower()
    return any(m in low for m in PLACEHOLDER_MARKERS)


def _org(scheme: dict) -> str:
    raw = str(scheme.get("organization") or scheme.get("organization_code") or "UNKNOWN").upper()
    if raw in {"NSFDC", "NBCFDC", "NSKFDC"}:
        return raw
    if "MINISTRY" in raw or "DEPARTMENT" in raw:
        return "MINISTRY/DEPARTMENT"
    if raw in {"", "NONE", "NULL"}:
        return "UNKNOWN"
    return raw


def audit_scheme(scheme: dict) -> dict[str, Any]:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    name = _join_langs(_loc(api.get("name")))
    desc = _join_langs(_loc(api.get("shortDescription")))
    org = _org(scheme)
    issues: list[str] = []
    if not name:
        issues.append("missing_name")
    if not scheme.get("organization"):
        issues.append("missing_organization")
    if not scheme.get("domain"):
        issues.append("missing_domain")
    if not scheme.get("assistance_type"):
        issues.append("missing_assistance_type")
    if _is_placeholder(desc) or not desc:
        issues.append("missing_or_placeholder_description")
    if not (scheme.get("source_url") or api.get("officialUrl") or api.get("sourceUrl")):
        issues.append("missing_source_url")
    if api.get("minLoanAmount") is None and api.get("maxLoanAmount") is None:
        issues.append("missing_loan_amounts")
    sid = str(scheme.get("scheme_id") or "")
    if len(sid) == 36 and sid.count("-") == 4 and not str(api.get("code") or "").startswith("NSFDC"):
        issues.append("uuid_id")
    quality = "INSUFFICIENT" if (
        "missing_or_placeholder_description" in issues and "missing_loan_amounts" in issues
    ) else ("PARTIAL" if issues else "SUFFICIENT")
    return {
        "scheme_id": sid,
        "name": name,
        "organization": org,
        "domain": scheme.get("domain"),
        "assistance_type": scheme.get("assistance_type"),
        "scheme_type": scheme.get("scheme_type"),
        "quality": quality,
        "issues": issues,
    }


def audit_catalogue(schemes_dir: Path | None = None) -> list[dict[str, Any]]:
    return [audit_scheme(s) for s in iter_schemes(schemes_dir)]


def iter_schemes(schemes_dir: Path | None = None) -> Iterable[dict]:
    root = schemes_dir or SCHEMES_DIR
    for path in sorted(root.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            yield json.load(f)


def _fmt_amount(val: Any) -> Optional[str]:
    try:
        return f"₹{int(float(val))}"
    except (TypeError, ValueError):
        return None


def _chunk(
    scheme: dict,
    section: str,
    text: str,
    idx: int,
    quality: str,
) -> Chunk:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    name = _join_langs(_loc(api.get("name"))) or str(scheme.get("scheme_id") or "unknown")
    source_url = str(scheme.get("source_url") or api.get("officialUrl") or api.get("sourceUrl") or "unknown")
    last_verified = str(api.get("lastUpdatedAt") or api.get("lastVerified") or "unknown")
    fin_status = "AVAILABLE" if api.get("minLoanAmount") is not None or api.get("maxLoanAmount") is not None else "UNKNOWN"
    citations = api.get("citations") if isinstance(api.get("citations"), list) else []
    source_id = ""
    if citations and isinstance(citations[0], dict):
        source_id = str(citations[0].get("id") or "")
    source_id = source_id or str(scheme.get("scheme_id") or "unknown")
    min_amt = api.get("minLoanAmount")
    max_amt = api.get("maxLoanAmount")
    try:
        min_f = float(min_amt) if min_amt is not None else None
    except (TypeError, ValueError):
        min_f = None
    try:
        max_f = float(max_amt) if max_amt is not None else None
    except (TypeError, ValueError):
        max_f = None
    sid = str(scheme.get("scheme_id") or "unknown")
    return Chunk(
        chunk_id=f"{sid}__{section}__{idx}",
        scheme_id=sid,
        scheme_name=name,
        section=section,
        language="en,hi",
        source_id=source_id,
        source_priority="1" if scheme.get("verified") else "3",
        financial_terms_status=fin_status,
        last_verified=last_verified,
        text=text.strip(),
        organization=_org(scheme),
        domain=str(scheme.get("domain") or "OTHER"),
        scheme_type=str(scheme.get("scheme_type") or "OTHER_FINANCIAL_ASSISTANCE"),
        purpose=str(scheme.get("purpose") or "GENERAL"),
        assistance_type=str(scheme.get("assistance_type") or "OTHER"),
        organization_code=str(scheme.get("organization_code") or _org(scheme)),
        source_url=source_url,
        verified=bool(scheme.get("verified") and api.get("verified") is not False),
        metadata_quality=quality,
        min_loan_amount=min_f,
        max_loan_amount=max_f,
    )


def chunks_for_scheme(scheme: dict) -> list[Chunk]:
    api = scheme.get("api") if isinstance(scheme.get("api"), dict) else {}
    audit = audit_scheme(scheme)
    quality = audit["quality"]
    name = _join_langs(_loc(api.get("name"))) or str(scheme.get("scheme_id"))
    desc = _join_langs(_loc(api.get("shortDescription")))
    org = _org(scheme)
    domain = str(scheme.get("domain") or "OTHER")
    assistance = str(scheme.get("assistance_type") or "OTHER")
    scheme_type = str(scheme.get("scheme_type") or "OTHER")
    purpose = str(scheme.get("purpose") or "GENERAL")
    chunks: list[Chunk] = []
    idx = 0

    overview_lines = [
        f"Scheme: {name}",
        f"scheme_id: {scheme.get('scheme_id')}",
        f"Organization: {org}",
        f"Domain: {domain}",
        f"Assistance type: {assistance}",
        f"Scheme type: {scheme_type}",
        f"Purpose: {purpose}",
    ]
    if desc and not _is_placeholder(desc):
        overview_lines.append(desc)
    else:
        overview_lines.append(
            "Authoritative narrative details are not available in the scheme record."
        )
    chunks.append(_chunk(scheme, "overview", "\n".join(overview_lines), idx, quality))
    idx += 1

    purpose_text = []
    if desc and not _is_placeholder(desc):
        purpose_text.append(f"Who this scheme is for / purpose:\n{desc}")
    purpose_text.append(f"Recorded purpose: {purpose}. Domain: {domain}.")
    chunks.append(_chunk(scheme, "purpose", "\n".join(purpose_text), idx, quality))
    idx += 1

    chunks.append(_chunk(
        scheme,
        "assistance_type",
        (
            f"{name} assistance type is {assistance} ({scheme_type}). "
            "This is a loan product." if assistance == "LOAN"
            else f"{name} assistance type is {assistance} ({scheme_type}). This is not classified as a loan."
        ),
        idx,
        quality,
    ))
    idx += 1

    min_s = _fmt_amount(api.get("minLoanAmount"))
    max_s = _fmt_amount(api.get("maxLoanAmount"))
    int_min = api.get("interestRateMinPct")
    int_max = api.get("interestRateMaxPct")
    tenure = api.get("maxTenureMonths")
    fin_lines = [f"Financial assistance recorded for {name}."]
    if min_s or max_s:
        fin_lines.append(f"Loan amount in scheme record: {min_s or 'unknown'} to {max_s or 'unknown'}.")
    else:
        fin_lines.append("Loan amount is not stated in the scheme record.")
    if int_min is not None or int_max is not None:
        fin_lines.append(f"Interest rate in scheme record: {int_min}% to {int_max}%.")
    else:
        fin_lines.append("Interest rate is not stated in the scheme record.")
    if tenure is not None:
        fin_lines.append(f"Maximum tenure in scheme record: {tenure} months.")
    chunks.append(_chunk(scheme, "financial_terms", "\n".join(fin_lines), idx, quality))
    idx += 1

    if desc and not _is_placeholder(desc):
        chunks.append(_chunk(
            scheme,
            "eligible_activities",
            f"Eligible activity notes for {name}:\n{desc}\nRecorded purpose: {purpose}.",
            idx,
            quality,
        ))
        idx += 1

    rules = api.get("eligibilityRules") if isinstance(api.get("eligibilityRules"), list) else []
    if rules:
        lines = [f"Eligibility criteria for {name}:"]
        income_lines = [f"Income criteria for {name}:"]
        edu_lines = [f"Education criteria for {name}:"]
        has_income = False
        has_edu = False
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            label = _join_langs(_loc(rule.get("label"))) or str(rule.get("field") or "")
            field = str(rule.get("field") or "")
            lines.append(f"- {label}")
            if "income" in field.lower() or "income" in label.lower():
                income_lines.append(f"- {label}")
                has_income = True
            if "education" in field.lower() or "course" in label.lower() or "admitted" in label.lower():
                edu_lines.append(f"- {label}")
                has_edu = True
        chunks.append(_chunk(scheme, "eligibility_criteria", "\n".join(lines), idx, quality))
        idx += 1
        if has_income:
            chunks.append(_chunk(scheme, "income_criteria", "\n".join(income_lines), idx, quality))
            idx += 1
        if has_edu:
            chunks.append(_chunk(scheme, "education_criteria", "\n".join(edu_lines), idx, quality))
            idx += 1
        elif api.get("maxAnnualFamilyIncome") is not None:
            chunks.append(_chunk(
                scheme,
                "income_criteria",
                f"Maximum annual family income in scheme record: {_fmt_amount(api.get('maxAnnualFamilyIncome'))}.",
                idx,
                quality,
            ))
            idx += 1
    elif api.get("maxAnnualFamilyIncome") is not None:
        chunks.append(_chunk(
            scheme,
            "income_criteria",
            f"Maximum annual family income in scheme record: {_fmt_amount(api.get('maxAnnualFamilyIncome'))}.",
            idx,
            quality,
        ))
        idx += 1

    docs = api.get("documentsRequired") if isinstance(api.get("documentsRequired"), list) else []
    if docs:
        doc_lines = [f"Documents listed for {name}:"]
        for doc in docs:
            label = _join_langs(_loc(doc)) if not isinstance(doc, str) else doc
            if label:
                doc_lines.append(f"- {label}")
        if len(doc_lines) > 1:
            chunks.append(_chunk(scheme, "documents", "\n".join(doc_lines), idx, quality))
            idx += 1

    repay = []
    if tenure is not None:
        repay.append(f"Maximum repayment tenure in scheme record: {tenure} months.")
    if api.get("moratoriumMinMonths") is not None:
        repay.append(
            f"Moratorium in scheme record: {api.get('moratoriumMinMonths')}–{api.get('moratoriumMaxMonths')} months."
        )
    if repay:
        chunks.append(_chunk(scheme, "repayment", f"Repayment for {name}:\n" + "\n".join(repay), idx, quality))
        idx += 1

    partners = api.get("channelPartnerTypes") if isinstance(api.get("channelPartnerTypes"), list) else []
    if partners or api.get("channelPartnerRequired") is not None:
        req = api.get("channelPartnerRequired")
        text = f"Channel partner information for {name}. Required: {req}."
        if partners:
            text += " Partner types in scheme record: " + ", ".join(str(p) for p in partners) + "."
        chunks.append(_chunk(scheme, "channel_partners", text, idx, quality))
        idx += 1

    if api.get("applicationUrl") or api.get("officialUrl"):
        chunks.append(_chunk(
            scheme,
            "application_process",
            (
                f"Application / official links for {name}. "
                f"Official URL: {api.get('officialUrl') or 'not stated'}. "
                f"Application URL: {api.get('applicationUrl') or 'not stated'}."
            ),
            idx,
            quality,
        ))
        idx += 1

    limit_lines = [f"Limitations for {name}."]
    if quality != "SUFFICIENT":
        limit_lines.append("Some catalogue fields are unknown or placeholder; do not invent missing facts.")
    if assistance != "LOAN":
        limit_lines.append("This record is not classified as a loan product.")
    chunks.append(_chunk(scheme, "limitations", "\n".join(limit_lines), idx, quality))
    idx += 1

    src = scheme.get("source_url") or api.get("officialUrl") or api.get("sourceUrl") or "unknown"
    chunks.append(_chunk(
        scheme,
        "source",
        f"Source for {name}: {scheme.get('source') or 'unknown'}. URL: {src}. Verified flag: {scheme.get('verified')}.",
        idx,
        quality,
    ))
    return chunks


def load_knowledge_chunks(schemes_dir: Path | None = None) -> list[Chunk]:
    out: list[Chunk] = []
    for scheme in iter_schemes(schemes_dir):
        out.extend(chunks_for_scheme(scheme))
    return out
