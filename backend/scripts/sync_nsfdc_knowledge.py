"""Idempotently merge researched official NSFDC facts into the local catalogue.

The source URLs below were manually audited on 2026-09-28. This script never
scrapes or invents defaults: it only applies the reviewed, versioned facts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SCHEMES = ROOT / "data" / "schemes"
RETRIEVED_AT = "2026-09-28"

CURRENT_SCHEME_SOURCE = {
    "source_url": "https://nsfdc.nic.in/scheme",
    "source_title": "NSFDC — Current Schemes",
    "source_document": "Official scheme catalogue page",
    "source_date": "2026",
    "retrieved_at": RETRIEVED_AT,
}
FAQ_SOURCE = {
    "source_url": "https://nsfdc.nic.in/faqs",
    "source_title": "NSFDC — Frequently Asked Questions",
    "source_document": "Official FAQ",
    "source_date": "2026",
    "retrieved_at": RETRIEVED_AT,
}
ELIGIBILITY_SOURCE = {
    "source_url": "https://nsfdc.nic.in/eligibility-requirements",
    "source_title": "NSFDC — Eligibility Requirements",
    "source_document": "Official eligibility page",
    "source_date": "2026-01-07",
    "retrieved_at": RETRIEVED_AT,
}
APPLICATION_SOURCE = {
    "source_url": "https://nsfdc.nic.in/how-to-apply-2",
    "source_title": "NSFDC — How to Apply",
    "source_document": "Official application procedure",
    "source_date": "2026",
    "retrieved_at": RETRIEVED_AT,
}
LEGACY_SOURCE = {
    "source_url": "https://nsfdc.nic.in/en/schemes/",
    "source_title": "NSFDC — Legacy English Scheme Catalogue",
    "source_document": "Older official English catalogue",
    "source_date": "2024-04-16",
    "retrieved_at": RETRIEVED_AT,
}


UPDATES: dict[str, dict[str, Any]] = {
    "nsfdc-mfs": {
        "status": "CURRENT_ACTIVE",
        "domain": "MICRO_ENTERPRISE",
        "purpose": "MICRO_ENTERPRISE",
        "supported_domains": ["BUSINESS", "MICRO_ENTERPRISE", "SERVICES"],
        "supported_purposes": ["SELF_EMPLOYMENT", "SMALL_BUSINESS", "MICRO_ENTERPRISE"],
        "provenance": [CURRENT_SCHEME_SOURCE, FAQ_SOURCE, ELIGIBILITY_SOURCE, APPLICATION_SOURCE],
        "api": {
            "channelPartnerRequired": True,
            "maxAnnualFamilyIncome": 500000,
            "officialUrl": CURRENT_SCHEME_SOURCE["source_url"],
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
    "nsfdc-term-loan": {
        "status": "CURRENT_ACTIVE",
        "domain": "BUSINESS",
        "purpose": "SELF_EMPLOYMENT",
        "supported_domains": [
            "BUSINESS", "AGRICULTURE", "LIVESTOCK", "SERVICES",
            "MANUFACTURING", "TRANSPORT",
        ],
        "supported_purposes": [
            "BUSINESS_STARTUP", "BUSINESS_EXPANSION", "SELF_EMPLOYMENT",
            "FARMING", "CROP_CULTIVATION", "DAIRY", "POULTRY",
            "MANUFACTURING", "SERVICE_BUSINESS", "TRANSPORT",
        ],
        "provenance": [CURRENT_SCHEME_SOURCE, FAQ_SOURCE, ELIGIBILITY_SOURCE, APPLICATION_SOURCE],
        "api": {
            "shortDescription": {
                "en": "Term finance for viable income-generating activities, including agriculture and allied activities, manufacturing, services, shops and transport.",
                "hi": "कृषि व संबद्ध गतिविधियों, विनिर्माण, सेवाओं, दुकान और परिवहन सहित व्यवहार्य आय-सृजन गतिविधियों के लिए सावधि वित्त।",
            },
            "channelPartnerRequired": True,
            "maxAnnualFamilyIncome": 500000,
            "officialUrl": CURRENT_SCHEME_SOURCE["source_url"],
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
    "nsfdc-amy": {
        "status": "CURRENT_ACTIVE",
        "domain": "MICRO_ENTERPRISE",
        "purpose": "MICRO_ENTERPRISE",
        "supported_domains": ["BUSINESS", "MICRO_ENTERPRISE", "SERVICES"],
        "supported_purposes": ["SELF_EMPLOYMENT", "SMALL_BUSINESS", "MICRO_ENTERPRISE"],
        "provenance": [CURRENT_SCHEME_SOURCE, FAQ_SOURCE, ELIGIBILITY_SOURCE, APPLICATION_SOURCE],
        "api": {
            "channelPartnerRequired": True,
            "maxAnnualFamilyIncome": 500000,
            "officialUrl": CURRENT_SCHEME_SOURCE["source_url"],
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
    "nsfdc-uny": {
        "status": "CURRENT_ACTIVE",
        "domain": "MICRO_ENTERPRISE",
        "scheme_type": "MICRO_FINANCE",
        "purpose": "MICRO_ENTERPRISE",
        "assistance_type": "LOAN",
        "supported_domains": ["BUSINESS", "MICRO_ENTERPRISE", "SERVICES"],
        "supported_purposes": ["SELF_EMPLOYMENT", "SMALL_BUSINESS", "MICRO_ENTERPRISE"],
        "provenance": [CURRENT_SCHEME_SOURCE, FAQ_SOURCE, ELIGIBILITY_SOURCE, APPLICATION_SOURCE],
        "api": {
            "channelPartnerRequired": True,
            "maxAnnualFamilyIncome": 500000,
            "officialUrl": CURRENT_SCHEME_SOURCE["source_url"],
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
    "nsfdc-education": {
        "status": "CURRENT_ACTIVE",
        "supported_domains": ["EDUCATION"],
        "supported_purposes": [
            "EDUCATION_LOAN", "HIGHER_EDUCATION", "PROFESSIONAL_COURSE",
            "TECHNICAL_COURSE", "DOCTORAL_STUDIES",
        ],
        "provenance": [CURRENT_SCHEME_SOURCE, FAQ_SOURCE, ELIGIBILITY_SOURCE, APPLICATION_SOURCE],
        "api": {
            "channelPartnerRequired": True,
            "maxAnnualFamilyIncome": 500000,
            "officialUrl": CURRENT_SCHEME_SOURCE["source_url"],
            "applicationUrl": "https://pmsuraj.dosje.gov.in/",
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
    # These records remain searchable for historical questions but cannot win
    # an active recommendation until a current official source confirms them.
    "nsfdc-msy": {
        "status": "UNCLEAR_STATUS",
        "provenance": [LEGACY_SOURCE],
        "api": {"lastVerified": RETRIEVED_AT, "verificationStatus": "STATUS_UNCLEAR"},
    },
    "nsfdc-gbs": {
        "status": "UNCLEAR_STATUS",
        "provenance": [LEGACY_SOURCE],
        "api": {"lastVerified": RETRIEVED_AT, "verificationStatus": "STATUS_UNCLEAR"},
    },
    "nsfdc-lvy": {
        "status": "UNCLEAR_STATUS",
        "provenance": [LEGACY_SOURCE],
        "api": {"lastVerified": RETRIEVED_AT, "verificationStatus": "STATUS_UNCLEAR"},
    },
    "0f2ed402-500b-5851-8bae-2f98070dac33": {
        "status": "CURRENT_ACTIVE",
        "domain": "SKILL_DEVELOPMENT",
        "scheme_type": "SKILL_TRAINING",
        "purpose": "SKILL_DEVELOPMENT",
        "assistance_type": "TRAINING",
        "organization": "MINISTRY/DEPARTMENT",
        "organization_code": "MOSJE",
        "implementing_organizations": ["NSFDC"],
        "supported_domains": ["SKILL_DEVELOPMENT"],
        "supported_purposes": [
            "UPSKILLING", "RESKILLING", "SHORT_TERM_TRAINING",
            "LONG_TERM_TRAINING", "ENTREPRENEURSHIP_DEVELOPMENT",
        ],
        "provenance": [FAQ_SOURCE, {
            "source_url": "https://nsfdc.nic.in/en/schemes/",
            "source_title": "NSFDC — PM-DAKSH Skill Development",
            "source_document": "Official NSFDC skill-development section",
            "source_date": "2024",
            "retrieved_at": RETRIEVED_AT,
        }],
        "api": {
            "shortDescription": {
                "en": "Free NSQF-compliant skill development for eligible Scheduled Caste persons aged 18–45 under PM-DAKSH; NSFDC is an implementing agency.",
                "hi": "पीएम-दक्ष के अंतर्गत 18–45 वर्ष के पात्र अनुसूचित जाति व्यक्तियों के लिए निःशुल्क NSQF-अनुरूप कौशल प्रशिक्षण; NSFDC एक कार्यान्वयन एजेंसी है।",
            },
            "officialUrl": "https://nsfdc.nic.in/faqs",
            "applicationUrl": "https://pmdaksh.dosje.gov.in/",
            "lastVerified": RETRIEVED_AT,
            "verificationStatus": "VERIFIED",
            "verified": True,
        },
    },
}


def merge(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            merge(base[key], value)
        else:
            base[key] = value
    return base


def main() -> None:
    changed = 0
    for sid, update in UPDATES.items():
        path = SCHEMES / f"{sid}.json"
        if not path.exists():
            raise FileNotFoundError(path)
        before = path.read_text(encoding="utf-8")
        data = json.loads(before)
        merge(data, update)
        data["source_url"] = update.get("provenance", [{}])[0].get(
            "source_url", data.get("source_url")
        )
        rendered = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
        if rendered != before:
            path.write_text(rendered, encoding="utf-8")
            changed += 1

    # Existing ministry catalogue shells are retained but explicitly marked
    # uncertain and non-recommendable. Their URLs remain useful provenance.
    for path in sorted(SCHEMES.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("status"):
            continue
        api = data.get("api") if isinstance(data.get("api"), dict) else {}
        url = (
            api.get("officialUrl")
            or api.get("sourceUrl")
            or data.get("source_url")
            or "unknown"
        )
        data["status"] = "UNCLEAR_STATUS"
        data["catalogue_visible"] = True
        data["provenance"] = [{
            "source_url": url,
            "source_title": api.get("sourceName") or "Existing catalogue source",
            "source_document": "Imported catalogue record",
            "source_date": api.get("lastVerified") or "unknown",
            "retrieved_at": RETRIEVED_AT,
        }]
        data["verified"] = bool(api.get("verified") is True)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        changed += 1
    print(f"Updated {changed} NSFDC records from reviewed official sources.")


if __name__ == "__main__":
    main()
