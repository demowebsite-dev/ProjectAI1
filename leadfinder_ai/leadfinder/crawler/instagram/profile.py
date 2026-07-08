"""Instagram profile crawler for LeadFinder AI.

Given an Instagram profile URL, navigates to the page via Playwright,
extracts the rendered HTML, and parses:

- Follower count
- Bio text
- Website URL
- Phone number (extracted from bio)

Architecture
------------
- :func:`parse_instagram_profile` — pure HTML parser (testable with fixture HTML)
- :class:`InstagramProfileCrawler` — async Playwright crawler (context manager)
- :func:`crawl_instagram_profile` — sync convenience wrapper for CLI use

Usage::

    from leadfinder.crawler.instagram.profile import crawl_instagram_profile

    data = crawl_instagram_profile("https://www.instagram.com/dreamhomerealty")
    print(data)
    # {
    #   "followers": 1234,
    #   "bio": "Premium real estate in Bangalore...",
    #   "website": "https://dreamhomerealty.in",
    #   "phone": "+919382380980",
    # }
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

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
from leadfinder.parser.website import has_website, clean_website_url
from leadfinder.parser.whatsapp import has_whatsapp
from leadfinder.utils.retry import with_retry

logger = logging.getLogger("leadfinder.crawler.instagram.profile")

# Load indicators for Instagram
_LOAD_INDICATORS = ["header[role='banner']", "main", "h1", "h2"]

# Selectors to dismiss dialogs
_DISMISS_SELECTORS = [
    "button[tabindex='0']",
    "[role='dialog'] button",
]


# ---------------------------------------------------------------------------
# Pure HTML parser
# ---------------------------------------------------------------------------

def parse_instagram_profile(html: str) -> dict:
    """Parse rendered Instagram profile HTML and extract business data.

    This function is side-effect free and can be tested with fixture HTML.

    Args:
        html: Rendered HTML of an Instagram profile page.

    Returns:
        Dict with keys: ``followers``, ``bio``, ``website``, ``phone``, ``whatsapp``.
    """
    result: dict = {
        "followers": None,
        "bio": None,
        "website": None,
        "phone": None,
        "whatsapp": False,
    }

    if not html or not html.strip():
        return result

    try:
        page = Selector(html, auto_match=False, adaptive=False)
    except Exception as exc:  # noqa: BLE001
        logger.error("Failed to parse Instagram HTML: %s", exc)
        return result

    full_text = str(page.get_all_text(separator="\n"))

    # ── Followers ────────────────────────────────────────────────────────────
    result["followers"] = parse_follower_count(full_text)

    # ── Bio ──────────────────────────────────────────────────────────────────
    result["bio"] = _extract_bio(page)

    # ── Website ──────────────────────────────────────────────────────────────
    result["website"] = _extract_website(page)

    # ── Phone ────────────────────────────────────────────────────────────────
    # Try bio text first, then full page
    bio_text = result["bio"] or ""
    result["phone"] = extract_first_phone(bio_text) or extract_first_phone(full_text)

    # ── WhatsApp ─────────────────────────────────────────────────────────────
    result["whatsapp"] = has_whatsapp(html)

    logger.debug(
        "Parsed Instagram profile: followers=%s bio=%r website=%r phone=%r whatsapp=%s",
        result["followers"], (result["bio"] or "")[:60],
        result["website"], result["phone"], result["whatsapp"],
    )
    return result


def _extract_bio(page: Selector) -> Optional[str]:
    """Extract the profile bio text from an Instagram page."""
    # Strategy 1: div/span with class containing 'bio'
    for selector in (".bio", ".bio-text", "[class*='bio']", "[class*='Bio']"):
        for el in page.css(selector):
            text = str(el.get_all_text(separator=" ")).strip()
            if text and len(text) > 3:
                return text

    # Strategy 2: <meta name="description"> (Instagram populates this)
    for meta in page.css("meta[name='description']"):
        content = meta.attrib.get("content", "").strip()
        if content:
            return content

    # Strategy 3: The first paragraph-ish block after the stats row
    for tag in ("p", "span"):
        for el in page.css(tag):
            text = str(el.get_all_text(separator=" ")).strip()
            # Bio is typically 20-500 chars
            if 20 < len(text) < 500 and not text.isdigit():
                return text

    return None


def _extract_website(page: Selector) -> Optional[str]:
    """Extract the external website link from an Instagram profile."""
    # Strategy 1: direct external links (Instagram uses rel="nofollow")
    for anchor in page.css("a[href][rel*='nofollow']"):
        href = anchor.attrib.get("href", "").strip()
        if href and has_website(href):
            return clean_website_url(href)

    # Strategy 2: any <a> with an external http link
    for anchor in page.css("a[href]"):
        href = anchor.attrib.get("href", "").strip()
        if href.startswith("http") and "instagram.com" not in href and has_website(href):
            return clean_website_url(href)

    return None


# ---------------------------------------------------------------------------
# Playwright crawler
# ---------------------------------------------------------------------------

class InstagramProfileCrawler:
    """Async context manager that crawls an Instagram business profile.

    Usage::

        async with InstagramProfileCrawler() as crawler:
            data = await crawler.crawl("https://www.instagram.com/dreamhomerealty")
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

    async def __aenter__(self) -> "InstagramProfileCrawler":
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=["--no-sandbox", "--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"],
        )
        logger.info("InstagramProfileCrawler browser launched")
        return self

    async def __aexit__(self, *_) -> None:
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("InstagramProfileCrawler browser closed")

    async def crawl(self, url: str) -> dict:
        """Navigate to *url* and extract Instagram profile data.

        Args:
            url: Full URL of an Instagram profile.

        Returns:
            Dict with keys: ``followers``, ``bio``, ``website``, ``phone``, ``whatsapp``.
        """
        if not self._browser:
            raise RuntimeError("Use InstagramProfileCrawler as an async context manager.")

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
            return parse_instagram_profile(html)
        finally:
            await context.close()

    @with_retry(max_retries=2, base_delay=2.0)
    async def _fetch_page(self, page: Page, url: str) -> str:
        await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
        await asyncio.sleep(settings.rate_limit_delay)

        for sel in _DISMISS_SELECTORS:
            try:
                await page.wait_for_selector(sel, timeout=1_500)
                await page.click(sel)
                await asyncio.sleep(0.3)
            except PlaywrightTimeoutError:
                pass

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

def crawl_instagram_profile(url: str, headless: bool = True) -> dict:
    """Synchronous wrapper around :class:`InstagramProfileCrawler`.

    Args:
        url:      Full Instagram profile URL.
        headless: Whether to run headlessly.

    Returns:
        Dict with keys: ``followers``, ``bio``, ``website``, ``phone``, ``whatsapp``.
    """
    async def _run() -> dict:
        async with InstagramProfileCrawler(headless=headless) as crawler:
            return await crawler.crawl(url)

    return asyncio.run(_run())
