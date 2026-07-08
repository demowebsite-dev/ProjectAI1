"""Follower count parser for LeadFinder AI.

Parses raw follower strings found on Facebook and Instagram pages
into plain integers.

Supported formats
-----------------
- "9 followers"
- "1,234 followers"
- "1.2K followers"
- "10K followers"
- "1.5M followers"
- "2.3M people like this"
- Raw numbers: "9", "1234"
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("leadfinder.parser.followers")

# Matches: optional leading whitespace, a number (with optional comma separators
# or decimal+suffix like 1.2K / 10K / 1.5M), captured as group 1+2
_FOLLOWER_RE = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*([KkMmBb]?)\s*(?:followers?|likes?|people)",
    re.IGNORECASE,
)

# Plain integer anywhere in text (fallback)
_PLAIN_INT_RE = re.compile(r"\b(\d[\d,]*)\b")

_MULTIPLIERS: dict[str, int] = {
    "k": 1_000,
    "m": 1_000_000,
    "b": 1_000_000_000,
}


def parse_follower_count(text: str) -> Optional[int]:
    """Parse a raw follower string into an integer count.

    Args:
        text: Raw string such as ``"9 followers"``, ``"1.2K likes"``,
              ``"10,234 people like this"``.

    Returns:
        Integer count, or *None* if nothing recognisable is found.

    Examples:
        >>> parse_follower_count("9 followers")
        9
        >>> parse_follower_count("1.2K followers")
        1200
        >>> parse_follower_count("10,234 people like this")
        10234
        >>> parse_follower_count("no followers here")
        None
    """
    if not text:
        return None

    match = _FOLLOWER_RE.search(text)
    if match:
        raw_num = match.group(1).replace(",", "")
        suffix = match.group(2).lower()
        try:
            value = float(raw_num)
            multiplier = _MULTIPLIERS.get(suffix, 1)
            return int(value * multiplier)
        except ValueError:
            pass

    # Fallback: handle bare "1.2K" or "10K" without the "followers" word
    bare_match = re.search(r"([\d,]+(?:\.\d+)?)\s*([KkMmBb])\b", text)
    if bare_match:
        raw_num = bare_match.group(1).replace(",", "")
        suffix = bare_match.group(2).lower()
        try:
            value = float(raw_num)
            return int(value * _MULTIPLIERS.get(suffix, 1))
        except ValueError:
            pass

    logger.debug("parse_follower_count: no match in %r", text[:80])
    return None
