"""Milestone 4 tests – Instagram Profile Analysis."""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from leadfinder.crawler.instagram.profile import (
    parse_instagram_profile,
    InstagramProfileCrawler,
    crawl_instagram_profile,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def instagram_html() -> str:
    return (FIXTURE_DIR / "instagram_profile_sample.html").read_text(encoding="utf-8")


@pytest.fixture()
def parsed_ig(instagram_html: str) -> dict:
    return parse_instagram_profile(instagram_html)


# ============================================================
# 1. parse_instagram_profile() — Pure parser tests
# ============================================================

class TestParseInstagramProfile:
    def test_returns_dict(self, parsed_ig: dict):
        assert isinstance(parsed_ig, dict)

    def test_has_all_keys(self, parsed_ig: dict):
        assert set(parsed_ig.keys()) == {"followers", "bio", "website", "phone", "whatsapp"}

    def test_followers_extracted(self, parsed_ig: dict):
        # Fixture has "1,234 followers"
        assert parsed_ig["followers"] == 1234

    def test_bio_extracted(self, parsed_ig: dict):
        assert parsed_ig["bio"] is not None
        assert "real estate" in parsed_ig["bio"].lower()

    def test_website_extracted(self, parsed_ig: dict):
        assert parsed_ig["website"] is not None
        assert "dreamhomerealty.in" in parsed_ig["website"]

    def test_phone_extracted_from_bio(self, parsed_ig: dict):
        # Bio contains "+91 93823 80980"
        assert parsed_ig["phone"] is not None
        assert "9382380980" in parsed_ig["phone"]

    def test_whatsapp_detected(self, parsed_ig: dict):
        assert parsed_ig["whatsapp"] is True

    def test_empty_html_returns_defaults(self):
        result = parse_instagram_profile("")
        assert result["followers"] is None
        assert result["bio"] is None
        assert result["website"] is None
        assert result["phone"] is None
        assert result["whatsapp"] is False

    def test_html_without_followers(self):
        html = "<html><body><p>Just a bio with no follower count.</p></body></html>"
        result = parse_instagram_profile(html)
        assert result["followers"] is None

    def test_html_with_external_link(self):
        html = (
            '<html><body>'
            '<a href="https://mybusiness.com" rel="nofollow">Visit</a>'
            '</body></html>'
        )
        result = parse_instagram_profile(html)
        assert result["website"] is not None
        assert "mybusiness.com" in result["website"]

    def test_html_without_website(self):
        html = '<html><body><p>No website here</p></body></html>'
        result = parse_instagram_profile(html)
        assert result["website"] is None

    def test_whatsapp_in_bio(self):
        html = (
            '<html><body>'
            '<span class="bio-text">DM for details wa.me/919382380980</span>'
            '</body></html>'
        )
        result = parse_instagram_profile(html)
        assert result["whatsapp"] is True

    def test_no_whatsapp(self):
        html = "<html><body><span class='bio-text'>No WA here just a bio</span></body></html>"
        result = parse_instagram_profile(html)
        assert result["whatsapp"] is False


# ============================================================
# 2. InstagramProfileCrawler — smoke tests
# ============================================================

class TestInstagramProfileCrawlerImport:
    def test_import(self):
        assert InstagramProfileCrawler is not None

    def test_sync_wrapper_callable(self):
        assert callable(crawl_instagram_profile)

    def test_requires_context_manager(self):
        crawler = InstagramProfileCrawler()

        async def _test():
            with pytest.raises(RuntimeError, match="context manager"):
                await crawler.crawl("https://instagram.com/test")

        asyncio.run(_test())

    def test_instantiation_with_settings(self):
        c = InstagramProfileCrawler(headless=True, timeout_ms=8000)
        assert c._headless is True
        assert c._timeout_ms == 8000


# ============================================================
# 3. crawl_instagram_profile — mocked via _fetch_page
# ============================================================

def _make_ig_mock(fixture_html: str):
    return patch.object(
        InstagramProfileCrawler,
        "_fetch_page",
        new=AsyncMock(return_value=fixture_html),
    )


class TestCrawlInstagramProfileMocked:
    def test_returns_dict(self, instagram_html: str):
        with _make_ig_mock(instagram_html):
            result = crawl_instagram_profile("https://instagram.com/test")
        assert isinstance(result, dict)

    def test_followers_via_mock(self, instagram_html: str):
        with _make_ig_mock(instagram_html):
            result = crawl_instagram_profile("https://instagram.com/test")
        assert result["followers"] == 1234

    def test_website_via_mock(self, instagram_html: str):
        with _make_ig_mock(instagram_html):
            result = crawl_instagram_profile("https://instagram.com/test")
        assert result["website"] is not None

    def test_phone_via_mock(self, instagram_html: str):
        with _make_ig_mock(instagram_html):
            result = crawl_instagram_profile("https://instagram.com/test")
        assert result["phone"] is not None

    def test_whatsapp_via_mock(self, instagram_html: str):
        with _make_ig_mock(instagram_html):
            result = crawl_instagram_profile("https://instagram.com/test")
        assert result["whatsapp"] is True
