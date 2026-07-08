"""Playwright-based Meta Ads Library searcher.

Navigates to the Meta Ads Library, runs a keyword + country search,
waits for the dynamic content to render, then hands the HTML off to
:mod:`leadfinder.crawler.meta.parser` for structured extraction.

Architecture
------------
Browser interaction is intentionally kept in this module.
All parsing logic lives in ``parser.py`` so it can be tested independently.

Usage::

    import asyncio
    from leadfinder.crawler.meta.searcher import MetaAdsSearcher

    async def main():
        async with MetaAdsSearcher() as searcher:
            results = await searcher.search("India", "Real Estate")
            for r in results:
                print(r.advertiser_name, r.cta, r.status)

    asyncio.run(main())
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional
from urllib.parse import quote_plus

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from leadfinder.config.settings import settings
from leadfinder.config.selectors import selectors
from leadfinder.crawler.meta.country_codes import resolve_country_code
from leadfinder.crawler.meta.parser import parse_ad_cards
from leadfinder.models.ad_result import AdResult
from leadfinder.utils.retry import with_retry

logger = logging.getLogger("leadfinder.crawler.meta.searcher")

# ---------------------------------------------------------------------------
# URL template
# ---------------------------------------------------------------------------
_ADS_LIBRARY_URL = (
    "https://www.facebook.com/ads/library/"
    "?active_status=active"
    "&ad_type=all"
    "&country={country}"
    "&q={keyword}"
    "&search_type=keyword_unordered"
    "&media_type=all"
)

# Selectors that indicate the ads have loaded
_LOADED_INDICATORS = [
    "[data-testid='ad-library-preview-card']",
    ".ad-card",                                    # our fixture class
    "div[role='main'] a[href*='facebook.com']",    # advertiser links
]

# Selectors for cookie / login dialogs to dismiss
_DISMISS_SELECTORS = [
    "button[data-testid='cookie-policy-manage-dialog-accept-button']",
    "button[title='Accept All']",
    "button[data-cookiebanner='accept_button']",
    "[aria-label='Close']",
    "div[role='dialog'] button",
]


class MetaAdsSearcher:
    """Async context manager that searches Meta Ads Library using Playwright.

    Use as an async context manager to ensure the browser is properly closed::

        async with MetaAdsSearcher() as searcher:
            ads = await searcher.search("India", "Real Estate", max_results=20)
    """

    def __init__(
        self,
        headless: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
        rate_limit_delay: Optional[float] = None,
    ) -> None:
        self._headless: bool = headless if headless is not None else settings.playwright_headless
        self._timeout_ms: int = timeout_ms if timeout_ms is not None else settings.request_timeout
        self._delay: float = rate_limit_delay if rate_limit_delay is not None else settings.rate_limit_delay
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None

    # ── Lifecycle ───────────────────────────────────────────────────────────

    async def __aenter__(self) -> "MetaAdsSearcher":
        """Launch the browser."""
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self._headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        logger.info("Browser launched (headless=%s)", self._headless)
        return self

    async def __aexit__(self, *_) -> None:
        """Close the browser and Playwright instance."""
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed.")

    # ── Public API ──────────────────────────────────────────────────────────

    async def search(
        self,
        country: str,
        keyword: str,
        max_results: int = 50,
    ) -> list[AdResult]:
        """Search Meta Ads Library and return parsed ad results.

        Args:
            country:     Country name or ISO code (e.g. ``"India"`` or ``"IN"``).
            keyword:     Search term (e.g. ``"Real Estate"``).
            max_results: Maximum number of ad results to return.

        Returns:
            List of :class:`~leadfinder.models.ad_result.AdResult` objects.

        Raises:
            ValueError:   If the country cannot be resolved.
            RuntimeError: If the browser has not been started (use as context manager).
        """
        if not self._browser:
            raise RuntimeError("MetaAdsSearcher must be used as an async context manager.")

        country_code = resolve_country_code(country)
        url = _ADS_LIBRARY_URL.format(
            country=country_code,
            keyword=quote_plus(keyword),
        )
        logger.info("Searching Meta Ads Library | country=%s keyword=%r url=%s", country_code, keyword, url)

        context: BrowserContext = await self._browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-US",
            timezone_id="Asia/Kolkata",
        )
        page: Page = await context.new_page()

        try:
            html = await self._fetch_ads_page(page, url)
            results = parse_ad_cards(html, country=country_code, keyword=keyword)
            logger.info("Found %d ad(s) before cap (max_results=%d)", len(results), max_results)
            return results[:max_results]
        finally:
            await context.close()

    # ── Internal helpers ────────────────────────────────────────────────────

    @with_retry(max_retries=3, base_delay=2.0, exceptions=(Exception,))
    async def _fetch_ads_page(self, page: Page, url: str) -> str:
        """Navigate to the URL and wait for ads to appear.

        Returns the rendered HTML string.
        """
        await page.goto(url, timeout=self._timeout_ms, wait_until="domcontentloaded")
        logger.debug("Navigated to %s", url)

        # Dismiss any cookie / login overlays
        await self._dismiss_dialogs(page)

        # Wait for at least one ad-related element to appear
        await self._wait_for_ads(page)

        # Rate-limit courtesy delay
        await asyncio.sleep(self._delay)

        return await page.content()

    async def _dismiss_dialogs(self, page: Page) -> None:
        """Try to dismiss cookie consent or login prompt dialogs."""
        for selector in _DISMISS_SELECTORS:
            try:
                await page.wait_for_selector(selector, timeout=2_000)
                await page.click(selector)
                logger.debug("Dismissed dialog with selector: %s", selector)
                await asyncio.sleep(0.5)
            except PlaywrightTimeoutError:
                pass  # Dialog not present – that's fine
            except Exception as exc:  # noqa: BLE001
                logger.debug("Could not dismiss dialog %s: %s", selector, exc)

    async def _wait_for_ads(self, page: Page) -> None:
        """Block until at least one ad element is visible or timeout occurs."""
        for indicator in _LOADED_INDICATORS:
            try:
                await page.wait_for_selector(indicator, timeout=self._timeout_ms)
                logger.debug("Ads loaded (indicator: %s)", indicator)
                return
            except PlaywrightTimeoutError:
                continue

        # If no indicator matched, log a warning but proceed anyway
        logger.warning(
            "None of the load indicators appeared within %dms. "
            "The page may have changed or access may be blocked.",
            self._timeout_ms,
        )


# ---------------------------------------------------------------------------
# Sync convenience wrapper  (used by CLI)
# ---------------------------------------------------------------------------

def search_meta_ads(
    country: str,
    keyword: str,
    max_results: int = 50,
    headless: bool = True,
) -> list[AdResult]:
    """Synchronous wrapper around :class:`MetaAdsSearcher`.

    Suitable for use in CLI commands or non-async contexts.

    Args:
        country:     Country name or ISO code.
        keyword:     Search keyword.
        max_results: Cap on number of results.
        headless:    Whether to run Playwright headlessly.

    Returns:
        List of :class:`~leadfinder.models.ad_result.AdResult`.
    """

    async def _run() -> list[AdResult]:
        async with MetaAdsSearcher(headless=headless) as searcher:
            return await searcher.search(country, keyword, max_results)

    return asyncio.run(_run())
