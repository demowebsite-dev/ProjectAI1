"""HTML parser for Meta Ads Library search results.

This module contains **pure functions** that accept raw HTML strings and return
structured :class:`~leadfinder.models.ad_result.AdResult` objects.

Keeping this layer browser-agnostic makes it independently unit-testable
without launching Playwright or hitting the network.

Design notes
------------
Meta Ads Library is a React SPA whose HTML structure changes frequently.
To stay resilient we apply a *layered* extraction strategy:

1. Try semantic/attribute-based selectors (most reliable).
2. Fall back to text-pattern matching.
3. Return ``None`` / empty defaults on failure — never crash.
"""

from __future__ import annotations

import logging
import re
from typing import Optional
from urllib.parse import urljoin

from scrapling import Selector

from leadfinder.models.ad_result import AdResult

logger = logging.getLogger("leadfinder.crawler.meta.parser")

# ---------------------------------------------------------------------------
# URL constants
# ---------------------------------------------------------------------------
_FB_BASE = "https://www.facebook.com"

# ---------------------------------------------------------------------------
# Known CTA button labels (used as a positive match list)
# ---------------------------------------------------------------------------
_KNOWN_CTAS: frozenset[str] = frozenset(
    {
        "learn more",
        "shop now",
        "sign up",
        "contact us",
        "book now",
        "get quote",
        "apply now",
        "download",
        "watch more",
        "send message",
        "get directions",
        "call now",
        "subscribe",
        "see menu",
        "get offer",
        "whatsapp",
        "chat on whatsapp",
        "message page",
    }
)

# ---------------------------------------------------------------------------
# Platform detection helpers
# ---------------------------------------------------------------------------
_PLATFORM_PATTERNS: dict[str, list[str]] = {
    "Facebook": ["facebook.com", "fb.com", "fbcdn.net", "facebook"],
    "Instagram": ["instagram.com", "cdninstagram.com", "instagram"],
    "Messenger": ["messenger.com", "messenger"],
    "Audience Network": ["audience_network", "audiencenetwork"],
}


def _detect_platforms_from_text(text: str) -> list[str]:
    """Infer platform names from text that mentions platform domains.

    Args:
        text: Any string (e.g. an image ``src``, aria-label, page text).

    Returns:
        List of recognised platform names found in *text*.
    """
    text_lower = text.lower()
    found: list[str] = []
    for platform, patterns in _PLATFORM_PATTERNS.items():
        if any(p in text_lower for p in patterns):
            found.append(platform)
    return found


def _detect_platforms_from_node(node: Selector) -> list[str]:
    """Try multiple strategies to determine which platforms an ad runs on.

    Args:
        node: A :class:`scrapling.Selector` for an ad card element.

    Returns:
        Deduplicated list of platform name strings; defaults to ``["Facebook"]``.
    """
    platforms: list[str] = []

    # Strategy 1: img src attributes
    for img in node.css("img"):
        src = img.attrib.get("src", "") or img.attrib.get("data-src", "")
        if src:
            platforms.extend(_detect_platforms_from_text(src))

    # Strategy 2: aria-label / title attributes
    for el in node.css("[aria-label]"):
        label = el.attrib.get("aria-label", "")
        if label:
            platforms.extend(_detect_platforms_from_text(label))
    for el in node.css("[title]"):
        title = el.attrib.get("title", "")
        if title:
            platforms.extend(_detect_platforms_from_text(title))

    # Strategy 3: scan all visible text
    full_text = str(node.get_all_text(separator=" "))
    platforms.extend(_detect_platforms_from_text(full_text))

    # Deduplicate while preserving insertion order
    seen: set[str] = set()
    result: list[str] = []
    for p in platforms:
        if p not in seen:
            seen.add(p)
            result.append(p)

    return result or ["Facebook"]  # sensible default


# ---------------------------------------------------------------------------
# Advertiser extraction
# ---------------------------------------------------------------------------

def _extract_advertiser(card: Selector) -> tuple[str, Optional[str]]:
    """Extract the advertiser display name and page URL from an ad card.

    Returns:
        ``(name, url)`` — ``url`` may be *None* if not found.
    """
    # Try <a> tags pointing to a Facebook page
    for anchor in card.css("a[href]"):
        href: str = anchor.attrib.get("href", "")
        if (
            "facebook.com" in href
            and "/ads/library" not in href
            and "/help" not in href
            and "/policies" not in href
        ):
            name = str(anchor.get_all_text(separator=" ")).strip()
            if name and len(name) < 200:
                url = href if href.startswith("http") else urljoin(_FB_BASE, href)
                return name, url

    # Fallback: first non-empty heading or strong text
    for tag in ("h1", "h2", "h3", "h4", "strong"):
        for el in card.css(tag):
            text = str(el.get_all_text(separator=" ")).strip()
            if text and len(text) < 200:
                return text, None

    return "Unknown Advertiser", None


# ---------------------------------------------------------------------------
# CTA extraction
# ---------------------------------------------------------------------------

def _extract_cta(card: Selector) -> Optional[str]:
    """Extract the CTA button label from an ad card.

    Args:
        card: A :class:`scrapling.Selector` for an ad card element.

    Returns:
        Title-cased CTA string (e.g. ``"Learn More"``), or *None*.
    """
    # Strategy 1: role="button" elements
    for btn in card.css("[role='button']"):
        text = str(btn.get_all_text(separator=" ")).strip().lower()
        if text in _KNOWN_CTAS:
            return text.title()

    # Strategy 2: <button> elements
    for btn in card.css("button"):
        text = str(btn.get_all_text(separator=" ")).strip().lower()
        if text in _KNOWN_CTAS:
            return text.title()

    # Strategy 3: scan all text for a known CTA phrase
    full_text = str(card.get_all_text(separator="\n")).lower()
    for cta in sorted(_KNOWN_CTAS, key=len, reverse=True):  # longest match first
        if cta in full_text:
            return cta.title()

    return None


# ---------------------------------------------------------------------------
# Status extraction
# ---------------------------------------------------------------------------

def _extract_status(card: Selector) -> str:
    """Determine whether the ad is Active or Inactive.

    Args:
        card: A :class:`scrapling.Selector` for an ad card element.

    Returns:
        ``"Active"``, ``"Inactive"``, or ``"Unknown"``.

    Note:
        We check for ``"inactive"`` *before* ``"active"`` because ``"inactive"``
        contains the substring ``"active"`` — order matters.
    """
    text = str(card.get_all_text(separator=" ")).lower()
    # Check Inactive first — "inactive" contains "active" as a substring
    if "inactive" in text or "ended" in text:
        return "Inactive"
    if "active" in text:
        return "Active"
    return "Unknown"


# ---------------------------------------------------------------------------
# Ad URL extraction
# ---------------------------------------------------------------------------

def _extract_ad_url(card: Selector) -> Optional[str]:
    """Extract a direct link to the ad detail page in the Ads Library.

    Args:
        card: A :class:`scrapling.Selector` for an ad card element.

    Returns:
        Full URL string if found, otherwise *None*.
    """
    for anchor in card.css("a[href]"):
        href: str = anchor.attrib.get("href", "")
        if "ads/library" in href and "id=" in href:
            return href if href.startswith("http") else urljoin(_FB_BASE, href)
    return None


# ---------------------------------------------------------------------------
# Card detection
# ---------------------------------------------------------------------------

def _find_ad_cards(page: Selector) -> list[Selector]:
    """Locate individual ad card elements on the rendered page.

    Tries multiple selector strategies and picks the one returning the most results.

    Args:
        page: A top-level :class:`scrapling.Selector` for the full page HTML.

    Returns:
        List of :class:`scrapling.Selector` nodes, one per ad card.
    """
    candidates: list[list] = []

    # Strategy 1: data-testid (React apps sometimes expose this)
    s1 = list(page.css("[data-testid='ad-library-preview-card']"))
    if s1:
        candidates.append(s1)

    # Strategy 2: aria-label containing "ad by" or "ad from"
    s2 = [
        el for el in page.css("[aria-label]")
        if "ad by" in (el.attrib.get("aria-label") or "").lower()
        or "ad from" in (el.attrib.get("aria-label") or "").lower()
    ]
    if s2:
        candidates.append(s2)

    # Strategy 3: divs with inline border-radius style that contain FB links
    s3 = [
        el for el in page.css("div[style*='border-radius']")
        if any("facebook.com" in (a.attrib.get("href", "")) for a in el.css("a[href]"))
    ]
    if s3:
        candidates.append(s3)

    # Strategy 4: our test fixture uses .ad-card
    s4 = list(page.css(".ad-card"))
    if s4:
        candidates.append(s4)

    if not candidates:
        logger.warning("No ad card containers found; falling back to full-page parse")
        return [page]

    return max(candidates, key=len)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_ad_cards(html: str, country: str, keyword: str) -> list[AdResult]:
    """Parse Meta Ads Library HTML and return a list of :class:`AdResult` objects.

    This function is the primary public interface of this module.
    It is intentionally side-effect-free so it can be unit-tested with fixture HTML.

    Args:
        html:    Raw HTML string of the rendered Meta Ads Library page.
        country: ISO country code used in the search (stored on each result).
        keyword: Search keyword used (stored on each result).

    Returns:
        List of :class:`AdResult` objects (may be empty if no cards are found).
    """
    if not html or not html.strip():
        logger.warning("parse_ad_cards received empty HTML for %s/%s", country, keyword)
        return []

    try:
        page = Selector(html, auto_match=False, adaptive=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse HTML with Scrapling: %s", exc)
        return []

    cards = _find_ad_cards(page)
    logger.info(
        "Found %d ad card(s) for keyword=%r country=%r", len(cards), keyword, country
    )

    results: list[AdResult] = []
    for i, card in enumerate(cards):
        try:
            name, adv_url = _extract_advertiser(card)
            result = AdResult(
                advertiser_name=name,
                advertiser_url=adv_url,
                ad_url=_extract_ad_url(card),
                cta=_extract_cta(card),
                platforms=_detect_platforms_from_node(card),
                status=_extract_status(card),
                country=country,
                keyword=keyword,
            )
            results.append(result)
            logger.debug(
                "Parsed ad %d: %s | cta=%s | status=%s",
                i + 1,
                name,
                result.cta,
                result.status,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipped ad card %d due to parse error: %s", i + 1, exc)

    return results
