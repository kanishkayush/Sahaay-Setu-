"""Indian mobile number normalisation for hackathon login."""

from __future__ import annotations

import re

INDIAN_MOBILE_RE = re.compile(r"^[6-9][0-9]{9}$")


def normalize_indian_mobile(raw: str | None) -> str | None:
    """Return a 10-digit Indian mobile or None if the input is not valid.

    Accepts optional +91 / 91 / 0 prefixes and separators.
    """
    if raw is None:
        return None
    digits = re.sub(r"\D", "", str(raw))
    if not digits:
        return None
    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]
    elif digits.startswith("0") and len(digits) == 11:
        digits = digits[1:]
    if not INDIAN_MOBILE_RE.fullmatch(digits):
        return None
    return digits
