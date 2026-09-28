"""Small semantic ontology shared by query expansion and evaluation.

This is metadata-driven expansion, not a scheme-selection keyword table.
"""

from __future__ import annotations


DOMAIN_CONCEPTS: dict[str, tuple[str, ...]] = {
    "EDUCATION": (
        "education", "higher education", "student finance",
        "professional technical course", "college fees", "पढ़ाई", "शिक्षा",
    ),
    "BUSINESS": (
        "business", "self employment", "enterprise", "working capital",
        "shop", "manufacturing", "service business", "व्यवसाय", "स्वरोजगार",
    ),
    "AGRICULTURE": (
        "agriculture", "farming", "farm livelihood", "crop cultivation",
        "agriculture allied activity", "खेती", "कृषि", "फसल",
    ),
    "LIVESTOCK": (
        "livestock", "dairy", "poultry", "animal husbandry",
        "पशुपालन", "डेयरी", "मुर्गी पालन",
    ),
    "SKILL_DEVELOPMENT": (
        "skill development", "training", "upskilling", "entrepreneurship training",
        "कौशल विकास", "प्रशिक्षण",
    ),
}

PURPOSE_CONCEPTS: dict[str, tuple[str, ...]] = {
    "EDUCATION_LOAN": ("educational loan", "student loan", "course financing", "शिक्षा ऋण"),
    "HIGHER_EDUCATION": ("higher education", "degree", "professional course"),
    "CROP_FARMING": ("crop farming", "crop cultivation", "फसल की खेती"),
    "RICE_FARMING": ("rice farming", "paddy cultivation", "धान की खेती"),
    "DAIRY_FARMING": ("dairy enterprise", "milk production", "डेयरी"),
    "POULTRY": ("poultry enterprise", "मुर्गी पालन"),
    "GENERAL_BUSINESS": ("business startup", "self employment", "small enterprise"),
}

ASSISTANCE_CONCEPTS: dict[str, tuple[str, ...]] = {
    "LOAN": ("loan", "credit", "finance", "ऋण", "लोन", "कर्ज"),
    "TRAINING": ("training", "skill programme", "प्रशिक्षण"),
    "SCHOLARSHIP": ("scholarship", "छात्रवृत्ति"),
}


def semantic_expansion(domain: str | None, purpose: str | None, assistance: str | None) -> str:
    concepts: list[str] = []
    concepts.extend(DOMAIN_CONCEPTS.get(str(domain or "").upper(), ()))
    concepts.extend(PURPOSE_CONCEPTS.get(str(purpose or "").upper(), ()))
    concepts.extend(ASSISTANCE_CONCEPTS.get(str(assistance or "").upper(), ()))
    return " ".join(dict.fromkeys(concepts))
