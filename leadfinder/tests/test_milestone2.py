"""Milestone 2 tests – Meta Ads Library: country codes, HTML parser, AdResult model, retry utility.

Test strategy
-------------
- country_codes  : pure unit tests (no I/O)
- parser         : unit tests against fixture HTML (no browser / network)
- AdResult model : pydantic validation tests
- retry utility  : functional tests with fake callables
- searcher       : smoke test (import + instantiation); live tests gated by env var
- CLI            : tests with mocked searcher (no browser)

Run live tests explicitly::

    LEADFINDER_LIVE_TESTS=1 pytest -m live
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from leadfinder.crawler.meta.country_codes import (
    resolve_country_code,
    list_supported_countries,
)
from leadfinder.crawler.meta.parser import (
    parse_ad_cards,
    _extract_cta,
    _extract_status,
    _detect_platforms_from_text,
)
from leadfinder.models.ad_result import AdResult
from leadfinder.utils.retry import with_retry
from leadfinder.cli.main import app

from typer.testing import CliRunner

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FIXTURE_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture()
def meta_ads_html() -> str:
    """Load the Meta Ads Library HTML fixture."""
    fixture_file = FIXTURE_DIR / "meta_ads_sample.html"
    assert fixture_file.exists(), f"Fixture not found: {fixture_file}"
    return fixture_file.read_text(encoding="utf-8")


@pytest.fixture()
def parsed_ads(meta_ads_html: str) -> list[AdResult]:
    """Parse fixture HTML and return AdResult list."""
    return parse_ad_cards(meta_ads_html, country="IN", keyword="Real Estate")


# ===========================================================================
# 1. Country Code Tests
# ===========================================================================

class TestCountryCodes:
    def test_india_by_name(self):
        assert resolve_country_code("India") == "IN"

    def test_india_by_code_uppercase(self):
        assert resolve_country_code("IN") == "IN"

    def test_india_by_code_lowercase(self):
        assert resolve_country_code("in") == "IN"

    def test_us_aliases(self):
        for alias in ("US", "us", "USA", "usa", "United States", "America"):
            assert resolve_country_code(alias) == "US", f"Failed for {alias!r}"

    def test_uk_aliases(self):
        for alias in ("UK", "uk", "United Kingdom", "GB", "Britain"):
            assert resolve_country_code(alias) == "GB", f"Failed for {alias!r}"

    def test_uae_aliases(self):
        for alias in ("UAE", "uae", "United Arab Emirates", "AE"):
            assert resolve_country_code(alias) == "AE"

    def test_all_special_code(self):
        assert resolve_country_code("ALL") == "ALL"
        assert resolve_country_code("all") == "ALL"

    def test_whitespace_stripped(self):
        assert resolve_country_code("  India  ") == "IN"

    def test_case_insensitive(self):
        assert resolve_country_code("INDIA") == "IN"
        assert resolve_country_code("india") == "IN"
        assert resolve_country_code("iNdIa") == "IN"

    def test_unknown_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown country"):
            resolve_country_code("Narnia")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError):
            resolve_country_code("")

    def test_list_supported_countries_returns_list(self):
        countries = list_supported_countries()
        assert isinstance(countries, list)
        assert len(countries) > 20

    def test_list_supported_countries_format(self):
        countries = list_supported_countries()
        # Each item is (name: str, code: str)
        for name, code in countries:
            assert isinstance(name, str)
            assert isinstance(code, str)
            assert len(code) == 2 or code == "ALL"

    def test_multiple_countries_resolve(self):
        expected = {
            "Australia": "AU",
            "Nigeria": "NG",
            "Singapore": "SG",
            "Brazil": "BR",
            "Germany": "DE",
            "Japan": "JP",
        }
        for name, code in expected.items():
            assert resolve_country_code(name) == code


# ===========================================================================
# 2. HTML Parser Tests
# ===========================================================================

class TestMetaAdsParser:
    def test_returns_list(self, meta_ads_html: str):
        results = parse_ad_cards(meta_ads_html, "IN", "Real Estate")
        assert isinstance(results, list)

    def test_correct_number_of_ads(self, parsed_ads: list[AdResult]):
        """Fixture contains 4 ad cards."""
        assert len(parsed_ads) == 4

    def test_all_items_are_ad_results(self, parsed_ads: list[AdResult]):
        for ad in parsed_ads:
            assert isinstance(ad, AdResult)

    def test_advertiser_names_extracted(self, parsed_ads: list[AdResult]):
        names = [ad.advertiser_name for ad in parsed_ads]
        assert "Dream Home Realty" in names
        assert "Sunshine Properties Pvt Ltd" in names
        assert "Green Valley Homes" in names
        assert "Skyline Realty India" in names

    def test_country_and_keyword_set(self, parsed_ads: list[AdResult]):
        for ad in parsed_ads:
            assert ad.country == "IN"
            assert ad.keyword == "Real Estate"

    def test_active_status_detected(self, parsed_ads: list[AdResult]):
        active = [ad for ad in parsed_ads if ad.status == "Active"]
        assert len(active) == 3

    def test_inactive_status_detected(self, parsed_ads: list[AdResult]):
        inactive = [ad for ad in parsed_ads if ad.status == "Inactive"]
        assert len(inactive) == 1
        assert inactive[0].advertiser_name == "Green Valley Homes"

    def test_cta_extracted(self, parsed_ads: list[AdResult]):
        ctas = {ad.cta for ad in parsed_ads if ad.cta}
        assert "Learn More" in ctas or "Contact Us" in ctas

    def test_ad_urls_extracted(self, parsed_ads: list[AdResult]):
        urls = [ad.ad_url for ad in parsed_ads if ad.ad_url]
        assert len(urls) > 0
        for url in urls:
            assert "ads/library" in url

    def test_platforms_not_empty(self, parsed_ads: list[AdResult]):
        for ad in parsed_ads:
            assert len(ad.platforms) > 0, f"No platforms for {ad.advertiser_name}"

    def test_facebook_platform_detected(self, parsed_ads: list[AdResult]):
        dream_home = next(ad for ad in parsed_ads if "Dream Home" in ad.advertiser_name)
        assert "Facebook" in dream_home.platforms

    def test_instagram_platform_detected(self, parsed_ads: list[AdResult]):
        dream_home = next(ad for ad in parsed_ads if "Dream Home" in ad.advertiser_name)
        assert "Instagram" in dream_home.platforms

    def test_empty_html_returns_empty_list(self):
        assert parse_ad_cards("", "IN", "test") == []

    def test_whitespace_only_html_returns_empty_list(self):
        assert parse_ad_cards("   \n   ", "IN", "test") == []

    def test_html_without_ads_returns_empty_or_fallback(self):
        html = "<html><body><p>No ads here</p></body></html>"
        result = parse_ad_cards(html, "IN", "test")
        # Should not crash; returns 0 or 1 (fallback full-page parse)
        assert isinstance(result, list)

    def test_malformed_html_does_not_raise(self):
        malformed = "<div><a href='http://facebook.com/test'>Name</a><span>Active</span>"
        result = parse_ad_cards(malformed, "US", "test")
        assert isinstance(result, list)


class TestParserHelpers:
    """Unit tests for internal helper functions."""

    def test_detect_platforms_facebook(self):
        platforms = _detect_platforms_from_text("static.xx.fbcdn.net/icon.png")
        assert "Facebook" in platforms

    def test_detect_platforms_instagram(self):
        platforms = _detect_platforms_from_text("cdninstagram.com/pic.jpg")
        assert "Instagram" in platforms

    def test_detect_platforms_both(self):
        text = "facebook.com/icon instagram.com/logo"
        platforms = _detect_platforms_from_text(text)
        assert "Facebook" in platforms
        assert "Instagram" in platforms

    def test_detect_platforms_unknown_returns_empty(self):
        platforms = _detect_platforms_from_text("somerandomain.com/image.jpg")
        assert platforms == []

    def test_extract_status_active(self):
        from scrapling import Selector
        html = "<div><span>Active</span></div>"
        node = Selector(html, auto_match=False, adaptive=False)
        assert _extract_status(node) == "Active"

    def test_extract_status_inactive(self):
        from scrapling import Selector
        html = "<div><span>Inactive</span></div>"
        node = Selector(html, auto_match=False, adaptive=False)
        assert _extract_status(node) == "Inactive"

    def test_extract_status_unknown(self):
        from scrapling import Selector
        html = "<div><span>Some other text</span></div>"
        node = Selector(html, auto_match=False, adaptive=False)
        assert _extract_status(node) == "Unknown"


# ===========================================================================
# 3. AdResult Model Tests
# ===========================================================================

class TestAdResultModel:
    def test_valid_model(self):
        ad = AdResult(
            advertiser_name="Test Co",
            country="IN",
            keyword="plumber",
        )
        assert ad.advertiser_name == "Test Co"
        assert ad.platforms == []
        assert ad.status == "Unknown"

    def test_full_model(self):
        ad = AdResult(
            advertiser_name="Skyline Realty",
            advertiser_url="https://facebook.com/skylinerealty",
            ad_url="https://facebook.com/ads/library/?id=999",
            cta="Learn More",
            platforms=["Facebook", "Instagram"],
            status="Active",
            country="IN",
            keyword="Real Estate",
        )
        assert ad.cta == "Learn More"
        assert "Instagram" in ad.platforms

    def test_name_is_required(self):
        with pytest.raises(Exception):
            AdResult(country="IN", keyword="test")

    def test_country_is_required(self):
        with pytest.raises(Exception):
            AdResult(advertiser_name="X", keyword="test")

    def test_keyword_is_required(self):
        with pytest.raises(Exception):
            AdResult(advertiser_name="X", country="IN")

    def test_platforms_defaults_to_empty_list(self):
        ad = AdResult(advertiser_name="X", country="US", keyword="test")
        assert ad.platforms == []

    def test_serialisation(self):
        ad = AdResult(
            advertiser_name="X", country="IN", keyword="test", status="Active"
        )
        d = ad.model_dump()
        assert d["advertiser_name"] == "X"
        assert d["status"] == "Active"


# ===========================================================================
# 4. Retry Utility Tests
# ===========================================================================

class TestRetryDecorator:
    def test_succeeds_on_first_try(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0)
        def ok():
            nonlocal call_count
            call_count += 1
            return "ok"

        assert ok() == "ok"
        assert call_count == 1

    def test_retries_on_failure_then_succeeds(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0)
        def flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("fail")
            return "ok"

        assert flaky() == "ok"
        assert call_count == 3

    def test_raises_after_max_retries(self):
        @with_retry(max_retries=2, base_delay=0)
        def always_fails():
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            always_fails()

    def test_does_not_retry_unfiltered_exceptions(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0, exceptions=(ValueError,))
        def type_error_func():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with pytest.raises(TypeError):
            type_error_func()
        # Should fail on first attempt without retrying
        assert call_count == 1

    def test_async_retry_succeeds(self):
        call_count = 0

        @with_retry(max_retries=3, base_delay=0)
        async def async_flaky():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise ConnectionError("retry me")
            return "done"

        result = asyncio.run(async_flaky())
        assert result == "done"
        assert call_count == 2

    def test_async_retry_exhausted_raises(self):
        @with_retry(max_retries=2, base_delay=0)
        async def async_always_fails():
            raise OSError("always broken")

        with pytest.raises(OSError):
            asyncio.run(async_always_fails())


# ===========================================================================
# 5. MetaAdsSearcher Smoke Tests (no browser)
# ===========================================================================

class TestMetaAdsSearcherImport:
    def test_import_searcher(self):
        from leadfinder.crawler.meta.searcher import MetaAdsSearcher
        assert MetaAdsSearcher is not None

    def test_import_sync_wrapper(self):
        from leadfinder.crawler.meta.searcher import search_meta_ads
        assert callable(search_meta_ads)

    def test_searcher_requires_context_manager(self):
        """Calling search() without entering context should raise RuntimeError."""
        from leadfinder.crawler.meta.searcher import MetaAdsSearcher
        searcher = MetaAdsSearcher()

        async def _test():
            with pytest.raises(RuntimeError, match="context manager"):
                await searcher.search("India", "Real Estate")

        asyncio.run(_test())

    def test_searcher_instantiation_settings(self):
        from leadfinder.crawler.meta.searcher import MetaAdsSearcher
        s = MetaAdsSearcher(headless=True, timeout_ms=5000, rate_limit_delay=0.5)
        assert s._headless is True
        assert s._timeout_ms == 5000
        assert s._delay == 0.5


# ===========================================================================
# 6. CLI Tests with Mocked Searcher
# ===========================================================================

class TestCLIWithMockedSearcher:
    """Test CLI search command with the browser mocked out."""

    def setup_method(self):
        self.runner = CliRunner()

    def _make_fake_ads(self) -> list[AdResult]:
        return [
            AdResult(
                advertiser_name="Dream Home Realty",
                advertiser_url="https://facebook.com/dreamhomerealty",
                ad_url="https://facebook.com/ads/library/?id=1",
                cta="Learn More",
                platforms=["Facebook", "Instagram"],
                status="Active",
                country="IN",
                keyword="Real Estate",
            ),
            AdResult(
                advertiser_name="Sunshine Properties",
                ad_url="https://facebook.com/ads/library/?id=2",
                cta="Contact Us",
                platforms=["Facebook"],
                status="Active",
                country="IN",
                keyword="Real Estate",
            ),
        ]

    def test_search_displays_ads_table(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LEADFINDER_DB_PATH", str(tmp_path / "cli2.db"))
        fake_ads = self._make_fake_ads()

        with patch(
            "leadfinder.cli.main.search_meta_ads",
            return_value=fake_ads,
        ):
            result = self.runner.invoke(
                app, ["search", "--country", "India", "--keyword", "Real Estate"]
            )

        assert result.exit_code == 0, result.output
        assert "Dream Home Realty" in result.output
        assert "Sunshine Properties" in result.output

    def test_search_saves_to_db(self, tmp_path, monkeypatch):
        db_path = str(tmp_path / "cli2_save.db")
        monkeypatch.setenv("LEADFINDER_DB_PATH", db_path)
        fake_ads = self._make_fake_ads()

        # Pre-create the DatabaseManager with the correct path so the CLI can use it
        # The CLI re-uses its module-level settings. We patch the DB directly.
        with patch("leadfinder.cli.main.search_meta_ads", return_value=fake_ads), \
             patch("leadfinder.cli.main.DatabaseManager") as mock_db_cls:
            # Set up a real in-memory DatabaseManager for the test
            from leadfinder.database.db import DatabaseManager as RealDB
            real_db = RealDB(db_path=db_path)
            mock_db_cls.return_value = real_db

            self.runner.invoke(
                app, ["search", "--country", "India", "--keyword", "Real Estate"]
            )

        # Verify records were saved into the patched DB
        from leadfinder.database.db import DatabaseManager as RealDB
        db = RealDB(db_path=db_path)
        businesses = db.list_businesses()
        assert len(businesses) == 2

    def test_search_invalid_country_exits_nonzero(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LEADFINDER_DB_PATH", str(tmp_path / "cli2_bad.db"))
        result = self.runner.invoke(
            app, ["search", "--country", "Narnia", "--keyword", "Wizard"]
        )
        assert result.exit_code != 0

    def test_search_no_ads_found(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LEADFINDER_DB_PATH", str(tmp_path / "cli2_empty.db"))
        with patch("leadfinder.cli.main.search_meta_ads", return_value=[]):
            result = self.runner.invoke(
                app, ["search", "--country", "India", "--keyword", "Plumber"]
            )
        assert result.exit_code == 0
        assert "No ads found" in result.output

    def test_search_shows_active_status(self, tmp_path, monkeypatch):
        monkeypatch.setenv("LEADFINDER_DB_PATH", str(tmp_path / "cli2_status.db"))
        fake_ads = self._make_fake_ads()
        with patch("leadfinder.cli.main.search_meta_ads", return_value=fake_ads), \
             patch("leadfinder.cli.main.DatabaseManager"):
            result = self.runner.invoke(
                app, ["search", "--country", "India", "--keyword", "Real Estate"]
            )
        # Rich may truncate column content; check for prefix 'Acti' (Active truncated)
        assert "Acti" in result.output or "Active" in result.output


# ===========================================================================
# 7. Live Integration Test (gated by env var)
# ===========================================================================

@pytest.mark.skipif(
    os.environ.get("LEADFINDER_LIVE_TESTS") != "1",
    reason="Live test skipped. Set LEADFINDER_LIVE_TESTS=1 to run.",
)
class TestLiveMetaAds:
    """Real browser + Meta Ads Library. Run manually or in CI with live flag."""

    def test_live_search_india_real_estate(self):
        from leadfinder.crawler.meta.searcher import search_meta_ads
        results = search_meta_ads("India", "Real Estate", max_results=5)
        assert isinstance(results, list)
        # We can't guarantee results but we can assert structure
        for r in results:
            assert isinstance(r, AdResult)
            assert r.country == "IN"
            assert r.keyword == "Real Estate"
            assert r.advertiser_name  # non-empty

    def test_live_search_us_dentist(self):
        from leadfinder.crawler.meta.searcher import search_meta_ads
        results = search_meta_ads("US", "Dentist", max_results=5)
        assert isinstance(results, list)
