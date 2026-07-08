"""Milestone 3 tests – Facebook Page Analysis.

Tests cover:
1. Follower parser — all formats including K/M suffixes
2. parse_facebook_page() — pure HTML parser with fixture
3. FacebookPageCrawler — import/instantiation smoke tests
4. crawl_facebook_page — mocked Playwright end-to-end
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

from leadfinder.parser.followers import parse_follower_count
from leadfinder.crawler.facebook.page import (
    parse_facebook_page,
    FacebookPageCrawler,
    crawl_facebook_page,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def facebook_html() -> str:
    return (FIXTURE_DIR / "facebook_page_sample.html").read_text(encoding="utf-8")


@pytest.fixture()
def parsed_fb(facebook_html: str) -> dict:
    return parse_facebook_page(facebook_html)


# ============================================================
# 1. Follower Count Parser
# ============================================================

class TestFollowerCountParser:
    def test_plain_number(self):
        assert parse_follower_count("9 followers") == 9

    def test_comma_separated(self):
        assert parse_follower_count("1,234 followers") == 1234

    def test_k_suffix_integer(self):
        assert parse_follower_count("10K followers") == 10_000

    def test_k_suffix_decimal(self):
        assert parse_follower_count("1.2K followers") == 1_200

    def test_m_suffix(self):
        assert parse_follower_count("1.5M followers") == 1_500_000

    def test_people_like_this(self):
        assert parse_follower_count("10,234 people like this") == 10_234

    def test_likes_label(self):
        assert parse_follower_count("5K likes") == 5_000

    def test_bare_k_suffix(self):
        assert parse_follower_count("15K") == 15_000

    def test_lowercase_k(self):
        assert parse_follower_count("2.5k followers") == 2_500

    def test_returns_none_for_empty(self):
        assert parse_follower_count("") is None

    def test_returns_none_for_no_match(self):
        assert parse_follower_count("no numbers here") is None

    def test_large_million(self):
        assert parse_follower_count("2.3M followers") == 2_300_000

    def test_nine_followers(self):
        assert parse_follower_count("9 followers") == 9

    def test_text_with_surrounding_content(self):
        text = "This page has 1,234 followers and is very popular"
        assert parse_follower_count(text) == 1_234


# ============================================================
# 2. parse_facebook_page() — Pure parser tests
# ============================================================

class TestParseFacebookPage:
    def test_returns_dict(self, parsed_fb: dict):
        assert isinstance(parsed_fb, dict)

    def test_has_all_keys(self, parsed_fb: dict):
        assert set(parsed_fb.keys()) == {"name", "followers", "phone", "website", "whatsapp"}

    def test_name_extracted(self, parsed_fb: dict):
        assert parsed_fb["name"] == "Dream Home Realty"

    def test_followers_extracted(self, parsed_fb: dict):
        assert parsed_fb["followers"] == 9

    def test_phone_extracted(self, parsed_fb: dict):
        assert parsed_fb["phone"] is not None
        assert "9382380980" in parsed_fb["phone"]

    def test_website_extracted(self, parsed_fb: dict):
        assert parsed_fb["website"] is not None
        assert "dreamhomerealty.in" in parsed_fb["website"]

    def test_whatsapp_detected(self, parsed_fb: dict):
        assert parsed_fb["whatsapp"] is True

    def test_empty_html_returns_defaults(self):
        result = parse_facebook_page("")
        assert result["name"] is None
        assert result["followers"] is None
        assert result["phone"] is None
        assert result["website"] is None
        assert result["whatsapp"] is False

    def test_html_without_followers(self):
        html = "<html><body><h1>Test Biz</h1></body></html>"
        result = parse_facebook_page(html)
        assert result["name"] == "Test Biz"
        assert result["followers"] is None

    def test_html_with_tel_link(self):
        # Use a known-valid Indian number with +91 prefix
        html = '<html><body><h1>X</h1><a href="tel:+919382380980">Call</a></body></html>'
        result = parse_facebook_page(html)
        assert result["phone"] is not None
        assert "9382380980" in result["phone"]

    def test_html_with_whatsapp_link(self):
        html = '<html><body><h1>Y</h1><a href="https://wa.me/911234567890">WA</a></body></html>'
        result = parse_facebook_page(html)
        assert result["whatsapp"] is True

    def test_html_without_whatsapp(self):
        html = "<html><body><h1>Z</h1><p>No WA here</p></body></html>"
        result = parse_facebook_page(html)
        assert result["whatsapp"] is False

    def test_facebook_redirect_website_decoded(self):
        html = (
            '<html><body><h1>Co</h1>'
            '<a href="https://l.facebook.com/l.php?u=https%3A%2F%2Fexample.com&h=AT1">Visit</a>'
            '</body></html>'
        )
        result = parse_facebook_page(html)
        assert result["website"] == "https://example.com"

    def test_no_website_returns_none(self):
        html = '<html><body><h1>Biz</h1><a href="https://www.facebook.com/biz">Self</a></body></html>'
        result = parse_facebook_page(html)
        assert result["website"] is None

    def test_name_from_title_tag(self):
        html = "<html><head><title>Biz Name - Home | Facebook</title></head><body></body></html>"
        result = parse_facebook_page(html)
        assert result["name"] == "Biz Name"


# ============================================================
# 3. FacebookPageCrawler — smoke tests
# ============================================================

class TestFacebookPageCrawlerImport:
    def test_import(self):
        assert FacebookPageCrawler is not None

    def test_sync_wrapper_callable(self):
        assert callable(crawl_facebook_page)

    def test_requires_context_manager(self):
        crawler = FacebookPageCrawler()

        async def _test():
            with pytest.raises(RuntimeError, match="context manager"):
                await crawler.crawl("https://facebook.com/test")

        asyncio.run(_test())

    def test_instantiation_with_settings(self):
        c = FacebookPageCrawler(headless=True, timeout_ms=5000)
        assert c._headless is True
        assert c._timeout_ms == 5000


# ============================================================
# 4. crawl_facebook_page — mocked (patch _fetch_page coroutine)
# ============================================================

FAKE_FB_RESULT = {
    "name": "Dream Home Realty",
    "followers": 9,
    "phone": "+919382380980",
    "website": "https://dreamhomerealty.in",
    "whatsapp": True,
}


def _make_fb_mock(fake_html: str):
    """Return a context manager that patches _fetch_page to return fake_html."""
    return patch.object(
        FacebookPageCrawler,
        "_fetch_page",
        new=AsyncMock(return_value=fake_html),
    )


class TestCrawlFacebookPageMocked:
    """Patch _fetch_page to avoid real browser launch. parse_facebook_page
    then runs on the fixture HTML and we assert on the parsed output."""

    def test_returns_dict(self, facebook_html: str):
        with _make_fb_mock(facebook_html):
            result = crawl_facebook_page("https://facebook.com/test")
        assert isinstance(result, dict)

    def test_name_extracted_via_mock(self, facebook_html: str):
        with _make_fb_mock(facebook_html):
            result = crawl_facebook_page("https://facebook.com/test")
        assert result["name"] == "Dream Home Realty"

    def test_followers_via_mock(self, facebook_html: str):
        with _make_fb_mock(facebook_html):
            result = crawl_facebook_page("https://facebook.com/test")
        assert result["followers"] == 9

    def test_whatsapp_true_via_mock(self, facebook_html: str):
        with _make_fb_mock(facebook_html):
            result = crawl_facebook_page("https://facebook.com/test")
        assert result["whatsapp"] is True

    def test_website_via_mock(self, facebook_html: str):
        with _make_fb_mock(facebook_html):
            result = crawl_facebook_page("https://facebook.com/test")
        assert result["website"] is not None
        assert "dreamhomerealty.in" in result["website"]
