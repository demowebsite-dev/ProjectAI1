"""Meta Ads Provider using GraphQL/XHR interception via Playwright.

Implements the MetaProvider adapter interface as specified:
- search_ads()
- collect_ads()
- normalize()
- validate()
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from urllib.parse import quote_plus

from playwright.async_api import async_playwright, Page, Response

from leadfinder.models.ad_result import AdResult
from leadfinder.crawler.meta.country_codes import resolve_country_code

logger = logging.getLogger("leadfinder.providers.meta.provider")

class MetaProvider:
    """Provider for Meta Ads Library using Playwright XHR/GraphQL interception."""

    def __init__(self) -> None:
        self.collected_responses: list[Any] = []

    def validate(self, raw_ad: dict[str, Any]) -> bool:
        """Validate if a raw dictionary contains necessary ad data.

        Args:
            raw_ad: A dictionary extracted from Meta's XHR/GraphQL JSON.

        Returns:
            True if it's a valid ad node, False otherwise.
        """
        if not isinstance(raw_ad, dict):
            return False
        
        # Checking for common fields in Meta's internal JSON representation
        has_name = any(k in raw_ad for k in ("pageName", "page_name", "advertiser_name"))
        has_id = any(k in raw_ad for k in ("pageID", "page_id", "adArchiveID"))
        return has_name and has_id

    def normalize(self, raw_ad: dict[str, Any]) -> AdResult:
        """Normalize third-party Meta data into our internal AdResult model.

        Never expose third-party data structures to the application.
        """
        name = raw_ad.get("pageName") or raw_ad.get("page_name") or raw_ad.get("advertiser_name") or "Unknown"
        profile_uri = raw_ad.get("pageProfileURI") or raw_ad.get("page_profile_uri") or raw_ad.get("advertiser_url")
        cta = raw_ad.get("cta_text") or raw_ad.get("call_to_action_text")
        status = raw_ad.get("status") or "Active"
        
        # Extract platforms (e.g., ["facebook", "instagram"])
        platforms = raw_ad.get("publisherPlatform") or raw_ad.get("publisher_platforms") or []
        if isinstance(platforms, str):
            platforms = [platforms]
            
        ad_id = raw_ad.get("adArchiveID") or raw_ad.get("ad_id")
        ad_url = f"https://www.facebook.com/ads/library/?id={ad_id}" if ad_id else None

        return AdResult(
            advertiser_name=name,
            advertiser_url=profile_uri,
            cta=cta,
            platforms=[str(p).capitalize() for p in platforms],
            status=status,
            ad_url=ad_url,
        )

    async def collect_ads(self, response: Response) -> None:
        """Playwright event handler for intercepting network responses.

        Listens specifically for GraphQL / API endpoints containing the ad data.
        """
        url = response.url
        if "graphql" in url or "api/graphql" in url:
            try:
                # Only process successful JSON responses
                if response.status == 200:
                    content_type = response.headers.get("content-type", "")
                    if "json" in content_type or "javascript" in content_type:
                        # Sometimes Meta sends JSON preceded by a "for (;;);" prefix for security
                        body_text = await response.text()
                        body_text = body_text.replace("for (;;);", "").strip()
                        
                        import json
                        # Meta sometimes returns multiple JSON objects separated by newlines
                        for line in body_text.split("\n"):
                            if line.strip():
                                data = json.loads(line)
                                self.collected_responses.append(data)
            except Exception as exc:  # noqa: BLE001
                # Fail gracefully if a single response fails to parse
                logger.debug("Failed to parse Meta XHR response: %s", exc)

    def _extract_ad_nodes(self, data: Any) -> list[dict]:
        """Recursively search a JSON payload for ad nodes."""
        found = []
        if isinstance(data, dict):
            if self.validate(data):
                found.append(data)
            for val in data.values():
                found.extend(self._extract_ad_nodes(val))
        elif isinstance(data, list):
            for item in data:
                found.extend(self._extract_ad_nodes(item))
        return found

    async def search_ads(self, country: str, keyword: str, max_results: int = 50) -> list[AdResult]:
        """Search Meta Ads Library via Playwright network interception.

        This replaces HTML scraping with robust XHR interception.
        """
        country_code = resolve_country_code(country)
        url = (
            f"https://www.facebook.com/ads/library/"
            f"?active_status=active&ad_type=all&country={country_code}"
            f"&q={quote_plus(keyword)}&search_type=keyword_unordered&media_type=all"
        )
        
        self.collected_responses = []
        normalized_results = []
        seen_names = set()
        
        logger.info("MetaProvider starting Playwright XHR capture for %s", url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            context = await browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Hook the network response event
            page.on("response", self.collect_ads)
            
            try:
                # Wait until network idle so initial GraphQL requests complete
                await page.goto(url, wait_until="networkidle", timeout=45000)
                
                # Scroll a few times to trigger more pagination XHR if needed
                for _ in range(3):
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(2)
            except Exception as exc:  # noqa: BLE001
                logger.warning("MetaProvider navigation encountered an issue, but will process captured responses: %s", exc)
            finally:
                await context.close()
                await browser.close()
            
        # Extract and normalize the captured data
        for resp in self.collected_responses:
            raw_ads = self._extract_ad_nodes(resp)
            for raw in raw_ads:
                ad_model = self.normalize(raw)
                
                # Deduplicate by advertiser name
                if ad_model.advertiser_name not in seen_names:
                    seen_names.add(ad_model.advertiser_name)
                    normalized_results.append(ad_model)
                    
                    if len(normalized_results) >= max_results:
                        return normalized_results
                            
        return normalized_results
