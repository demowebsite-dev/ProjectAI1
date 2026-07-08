"""WhatsApp contact detector for LeadFinder AI.

Detects WhatsApp presence by scanning text/HTML for:
- wa.me links
- api.whatsapp.com links
- "Chat on WhatsApp" text
- WhatsApp button labels

Full tests are in Milestone 6. Used by crawlers from M3 onward.
"""

from __future__ import annotations

import re
import logging
from typing import Optional

logger = logging.getLogger("leadfinder.parser.whatsapp")

# Patterns that indicate a WhatsApp contact option
_WHATSAPP_URL_PATTERNS = [
    "wa.me/",
    "api.whatsapp.com/send",
    "api.whatsapp.com/phone",
    "web.whatsapp.com",
]

_WHATSAPP_TEXT_PATTERNS = [
    "chat on whatsapp",
    "whatsapp us",
    "message on whatsapp",
    "whatsapp button",
    "whatsapp",
]

# Regex to extract number from wa.me/NUMBER or wa.me/+NUMBER
_WA_NUMBER_RE = re.compile(r"wa\.me/\+?(\d+)", re.IGNORECASE)


def has_whatsapp(text_or_html: str) -> bool:
    """Return True if the text/HTML contains any WhatsApp contact indicators.

    Checks for wa.me links, api.whatsapp.com, and common button labels.

    Args:
        text_or_html: Raw HTML or plain text to scan.

    Returns:
        True if WhatsApp contact is detectable.
    """
    if not text_or_html:
        return False

    lower = text_or_html.lower()

    for pattern in _WHATSAPP_URL_PATTERNS:
        if pattern in lower:
            logger.debug("WhatsApp detected via URL pattern: %s", pattern)
            return True

    for pattern in _WHATSAPP_TEXT_PATTERNS:
        if pattern in lower:
            logger.debug("WhatsApp detected via text pattern: %s", pattern)
            return True

    return False


def extract_whatsapp_number(text_or_html: str) -> Optional[str]:
    """Extract a phone number from a wa.me link if present.

    Args:
        text_or_html: Raw HTML or text containing a potential wa.me link.

    Returns:
        Digits-only phone number string (e.g. ``"919382380980"``), or *None*.
    """
    match = _WA_NUMBER_RE.search(text_or_html)
    if match:
        return match.group(1)
    return None
