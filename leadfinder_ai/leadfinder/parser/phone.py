"""Phone number extractor for LeadFinder AI.

Provides regex-based extraction of raw phone strings from text,
and normalisation via the ``phonenumbers`` library.

Full unit tests are in Milestone 5. This module is used by crawlers from M3 onward.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

try:
    import phonenumbers
    from phonenumbers import PhoneNumberFormat, NumberParseException
    _HAS_PHONENUMBERS = True
except ImportError:  # pragma: no cover
    _HAS_PHONENUMBERS = False

logger = logging.getLogger("leadfinder.parser.phone")

# Regex: capture phone-like patterns (international + local formats)
# Matches: +91-9382-380980, +1 (555) 123-4567, 9382380980, etc.
_PHONE_RE = re.compile(
    r"""
    (?:
        (?:\+\d{1,3}[\s\-.]?)       # International prefix: +91, +1, etc.
        (?:[\s\-.]?\(?\d{1,4}\)?)   # Optional area code
        [\s\-.]?
        \d{3,5}
        [\s\-.]?
        \d{3,5}
        (?:[\s\-.]?\d{1,5})?        # Optional extension
    |
        \b\d{10}\b                  # Plain 10-digit
    )
    """,
    re.VERBOSE,
)

# Minimum digits to be considered a phone number
_MIN_DIGITS = 7


def extract_phones(text: str) -> list[str]:
    """Scan *text* for phone-like patterns and return raw matched strings.

    Args:
        text: Any string (page text, HTML-stripped content).

    Returns:
        List of raw phone strings found (not normalised).
    """
    if not text:
        return []
    candidates = _PHONE_RE.findall(text)
    # Filter out strings with too few digits
    return [
        c.strip() for c in candidates
        if sum(ch.isdigit() for ch in c) >= _MIN_DIGITS
    ]


def normalize_phone(raw: str, default_region: str = "IN") -> Optional[str]:
    """Normalise a raw phone string to E.164 format using the phonenumbers library.

    Args:
        raw:            Raw phone string (e.g. ``"+91 9382 380980"``).
        default_region: ISO country code to assume when no international prefix is present.

    Returns:
        E.164-formatted string (e.g. ``"+919382380980"``), or *None* on failure.
    """
    if not _HAS_PHONENUMBERS:  # pragma: no cover
        return raw.strip() or None

    try:
        parsed = phonenumbers.parse(raw, default_region)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, PhoneNumberFormat.E164)
    except NumberParseException as exc:
        logger.debug("normalize_phone failed for %r: %s", raw, exc)
    return None


def is_valid_phone(number: str, default_region: str = "IN") -> bool:
    """Return True if *number* is a valid phone number.

    Args:
        number:         Phone string to validate.
        default_region: Region to assume for numbers without a country prefix.
    """
    if not _HAS_PHONENUMBERS:  # pragma: no cover
        return bool(extract_phones(number))
    try:
        parsed = phonenumbers.parse(number, default_region)
        return phonenumbers.is_valid_number(parsed)
    except Exception:  # noqa: BLE001
        return False


def extract_first_phone(text: str, default_region: str = "IN") -> Optional[str]:
    """Convenience: extract the first valid phone number from *text*, normalised.

    Args:
        text:           Text to scan.
        default_region: Default region for number parsing.

    Returns:
        First valid E.164 phone string found, or *None*.
    """
    for raw in extract_phones(text):
        normalised = normalize_phone(raw, default_region)
        if normalised:
            return normalised
    return None
