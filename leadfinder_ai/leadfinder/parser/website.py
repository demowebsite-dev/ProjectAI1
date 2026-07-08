"""Website URL detector and extractor for LeadFinder AI.

Handles Facebook's redirect URL pattern (l.facebook.com/l.php?u=...)
and validates whether a URL represents a real external website.

Full tests are in Milestone 7. Used by crawlers from M3 onward.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import parse_qs, unquote, urlparse

logger = logging.getLogger("leadfinder.parser.website")

# Social media domains — these are NOT "websites" for our purposes
_SOCIAL_DOMAINS = frozenset(
    {
        "facebook.com",
        "www.facebook.com",
        "m.facebook.com",
        "instagram.com",
        "www.instagram.com",
        "twitter.com",
        "x.com",
        "linkedin.com",
        "youtube.com",
        "wa.me",
        "api.whatsapp.com",
        "web.whatsapp.com",
    }
)


def extract_website_from_facebook_redirect(href: str) -> Optional[str]:
    """Decode an outgoing URL from a Facebook redirect link.

    Facebook wraps external links as:
    ``https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com&...``

    Args:
        href: The raw href value of an anchor element.

    Returns:
        The decoded destination URL, or *None* if not a Facebook redirect.
    """
    if not href:
        return None

    try:
        parsed = urlparse(href)
    except Exception:
        return None

    # Facebook redirect pattern
    if "l.facebook.com" in parsed.netloc or "l.facebook.com" in href:
        qs = parse_qs(parsed.query)
        target = qs.get("u", [None])[0]
        if target:
            return unquote(target)

    # Direct non-Facebook external link
    if parsed.scheme in ("http", "https") and parsed.netloc:
        domain = parsed.netloc.lstrip("www.")
        if not any(social in parsed.netloc for social in _SOCIAL_DOMAINS):
            return href

    return None


def has_website(value: Optional[str]) -> bool:
    """Return True if *value* represents a real external website.

    Social media URLs and empty strings return False.

    Args:
        value: A URL string or *None*.

    Returns:
        True if the URL looks like a standalone business website.
    """
    if not value or not value.strip():
        return False

    try:
        parsed = urlparse(value.strip())
    except Exception:
        return False

    if parsed.scheme not in ("http", "https"):
        return False

    netloc = parsed.netloc.lower().lstrip("www.")
    return not any(domain in parsed.netloc.lower() for domain in _SOCIAL_DOMAINS)


def clean_website_url(url: str) -> str:
    """Normalise a website URL: ensure scheme, strip trailing slash.

    Args:
        url: Raw URL string.

    Returns:
        Cleaned URL string.
    """
    url = url.strip()
    if url and not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url.rstrip("/")
