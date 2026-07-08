"""Facebook Page crawler for LeadFinder AI.

Given a Facebook Page URL, this module navigates to the page using Playwright,
extracts the rendered HTML, and parses key business data:

- Business name
- Follower count
- Phone number
- Website URL
- WhatsApp availability

Architecture
------------
- :class:`FacebookPageCrawler` — async Playwright-based crawler (context manager)
- :func:`parse_facebook_page` — pure HTML parser (testable with fixture HTML)
- :func:`crawl_facebook_page` — sync convenience wrapper for CLI use

Usage::

    from leadfinder.crawler.facebook.page import crawl_facebook_page

    data = crawl_facebook_page("https://www.facebook.com/dreamhomerealty")
    print(data)
    # {
    #   "name": "Dream Home Realty",
    #   "followers": 9,
    #   "phone": "+919382380980",
    #   "website": "https://dreamhomerealty.in",
    #   "whatsapp": True,
    # }
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional
from urllib.parse import urljoin

from playwright.async_api import (
    Browser,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)
from scrapling import Selector

from leadfinder.config.settings import settings
from leadfinder.parser.followers import parse_follower_count
from leadfinder.parser.phone import extract_first_phone
from leadfinder.parser.website import extract_website_from_facebook_redirect
from leadfinder.parser.whatsapp import has_whatsapp, extract_whatsapp_number
from leadfinder.utils.retry import with_retry

logger = logging.getLogger("leadfinder.crawler.facebook.page")

_FB_BASE = "https://www.facebook.com"

# Selectors to wait for before scraping
_LOAD_INDICATORS = ["h1", "[role='main']", "div[data-pagelet]"]

# Dialog / cookie selectors to dismiss
_DISMISS_SELECTORS = [
    "[data-testid='cookie-policy-manage-dialog-accept-button']",
    "button[title='Accept All']",
    "div[aria-label='Close']",
    "div[role='dialog'] button",
]


# ---------------------------------------------------------------------------
# Pure HTML parser (no Playwright — fully unit-testable)
# ---------------------------------------------------------------------------

def parse_facebook_page(html: str) -> dict:
    """Parse rendered Facebook page HTML and return extracted business data.

    This function is side-effect free and can be tested with fixture HTML.

    Args:
        html: Rendered HTML of a Facebook business page.

    Returns:
        Dict with keys: ``name``, ``followers``, ``phone``, ``website``, ``whatsapp``.
        Values may be *None* / *False* if not found.
    """
    result: dict = {
        "name": None,
        "followers": None,
        "phone": None,
        "website": None,
        "whatsapp": False,
    }

    if not html or not html.strip():
        return result

    try:
        page = Selector(html, auto_match=False, adaptive=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse Facebook page HTML: %s", exc)
        return result

    # ── Name ────────────────────────────────────────────────────────────────
    result["name"] = _extract_page_name(page)

    # ── Followers ───────────────────────────────────────────────────────────
    full_text = str(page.get_all_text(separator="\n"))
    result["followers"] = parse_follower_count(full_text)

    # ── Phone ───────────────────────────────────────────────────────────────
    result["phone"] = _extract_phone(page, full_text)

    # ── Website ─────────────────────────────────────────────────────────────
    result["website"] = _extract_website(page)

    # ── WhatsApp ────────────────────────────────────────────────────────────
    result["whatsapp"] = has_whatsapp(html)

    logger.debug(
        "Parsed Facebook page: name=%r followers=%s phone=%r website=%r whatsapp=%s",
        result["name"], result["followers"], result["phone"],
        result["website"], result["whatsapp"],
    )
    return result


def _extract_page_name(page: Selector) -> Optional[str]:
    """Extract the business name from a Facebook page."""
    # Strategy 1: <h1> tag (most reliable)
    for h1 in page.css("h1"):
        text = str(h1.get_all_text(separator=" ")).strip()
        if text and len(text) < 200:
            return text

    # Strategy 2: <title> tag, strip " - Home | Facebook" suffix
    for title in page.css("title"):
        text = str(title.get_all_text(separator=" ")).strip()
        for suffix in (" - Home | Facebook", " | Facebook", " - Facebook"):
            if suffix in text:
                return text.replace(suffix, "").strip()

    # Strategy 3: page-name class
    for el in page.css(".page-name"):
        text = str(el.get_all_text(separator=" ")).strip()
        if text:
            return text

    return None


def _extract_phone(page: Selector, full_text: str) -> Optional[str]:
    """Extract and normalise a phone number from the page."""
    # Strategy 1: tel: links (most reliable)
    for anchor in page.css("a[href^='tel:']"):
        raw = anchor.attrib.get("href", "").replace("tel:", "").strip()
        if raw:
            from leadfinder.parser.phone import normalize_phone
            normalised = normalize_phone(raw)
            if normalised:
                return normalised

    # Strategy 2: scan full text for phone patterns
    return extract_first_phone(full_text)


def _extract_website(page: Selector) -> Optional[str]:
    """Extract an external website URL from Facebook redirect links."""
    for anchor in page.css("a[href]"):
        href = anchor.attrib.get("href", "")
        website = extract_website_from_facebook_redirect(href)
        if website:
            return website
    return None


# ---------------------------------------------------------------------------
# Playwright crawler
# ---------------------------------------------------------------------------

class FacebookPageCrawler:
    """Async context manager that crawls a Facebook business page.

    Usage::

        async with FacebookPageCrawler() as crawler:
            data = await crawler.crawl("https://www.facebook.com/dreamhomerealty")
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
    ) -> None:
        self._headless: bool = headless if headless is not None else settings.playwright_headless
        self._timeout_ms: int = timeout_ms if timeout_ms is not None else settings.request_timeout
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    async def __aenter__(self) -> "FacebookPageCrawler":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        logger.info("FacebookPageCrawler browser launched")
        return self

    async def __aexit__(self, *_) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("FacebookPageCrawler browser closed")

    async def crawl(self, url: str) -> dict:
        """Navigate to *url* and extract business data.

        Args:
            url: Full URL of a Facebook business page.

        Returns:
            Dict with keys: ``name``, ``followers``, ``phone``, ``website``, ``whatsapp``.
        """
        if not self._browser:
            raise RuntimeError("Use FacebookPageCrawler as an async context manager.")

        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )
        page: Page = await context.new_page()
        try:
            html = await self._fetch_page(page, url)
            return parse_facebook_page(html)
        finally:
            await context.close()

    @with_retry(max_retries=2, base_delay=2.0)
    async def _fetch_page(self, page: Page, url: str) -> str:
        await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
        await asyncio.sleep(settings.rate_limit_delay)

        # Dismiss overlays
        for sel in _DISMISS_SELECTORS:
            try:
                await page.wait_for_selector(sel, timeout=1_500)
                await page.click(sel)
                await asyncio.sleep(0.3)
            except PlaywrightTimeoutError:
                pass

        # Wait for content
        for indicator in _LOAD_INDICATORS:
            try:
                await page.wait_for_selector(indicator, timeout=self._timeout_ms)
                break
            except PlaywrightTimeoutError:
                continue

        return await page.content()


# ---------------------------------------------------------------------------
# Sync convenience wrapper
# ---------------------------------------------------------------------------

def crawl_facebook_page(url: str, headless: bool = True) -> dict:
    """Synchronous wrapper around :class:`FacebookPageCrawler`.

    Args:
        url:      Full Facebook page URL.
        headless: Whether to run headlessly.

    Returns:
        Dict with keys: ``name``, ``followers``, ``phone``, ``website``, ``whatsapp``.
    """
    async def _run() -> dict:
        async with FacebookPageCrawler(headless=headless) as crawler:
            return await crawler.crawl(url)

    return asyncio.run(_run())
