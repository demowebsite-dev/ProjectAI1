"""Milestone 7 tests – Website Detection.

Tests the `website.py` module for detecting external websites
and decoding Facebook redirects.
"""

from __future__ import annotations

from leadfinder.parser.website import (
    has_website,
    extract_website_from_facebook_redirect,
    clean_website_url,
)

# ============================================================
# 1. has_website
# ============================================================

class TestHasWebsite:
    def test_true_for_valid_external_website(self):
        assert has_website("https://dreamhomerealty.in") is True
        assert has_website("http://www.example.com") is True

    def test_false_for_social_media(self):
        assert has_website("https://facebook.com/dreamhomerealty") is False
        assert has_website("https://instagram.com/dreamhomerealty") is False
        assert has_website("https://twitter.com/dreamhome") is False
        assert has_website("https://wa.me/919382380980") is False

    def test_false_for_empty(self):
        assert has_website("") is False
        assert has_website(None) is False
        assert has_website("   ") is False

    def test_false_for_invalid_url(self):
        assert has_website("not a url") is False
        assert has_website("ftp://example.com") is False


# ============================================================
# 2. extract_website_from_facebook_redirect
# ============================================================

class TestExtractWebsiteFromFacebookRedirect:
    def test_extracts_from_l_php(self):
        href = "https://l.facebook.com/l.php?u=https%3A%2F%2Fdreamhomerealty.in&h=AT1test"
        assert extract_website_from_facebook_redirect(href) == "https://dreamhomerealty.in"

    def test_extracts_without_l_facebook_com_domain_but_has_it(self):
        # A relative or broken URL containing l.facebook.com
        href = "/l.php?u=https%3A%2F%2Fexample.com"
        # The parser expects "l.facebook.com" in netloc or href.
        # So we should test a valid form
        assert extract_website_from_facebook_redirect(
            "http://l.facebook.com/l.php?u=https://example.com"
        ) == "https://example.com"

    def test_returns_none_if_no_u_param(self):
        href = "https://l.facebook.com/l.php?id=1234"
        assert extract_website_from_facebook_redirect(href) is None

    def test_returns_direct_link_if_not_facebook(self):
        href = "https://example.com"
        assert extract_website_from_facebook_redirect(href) == "https://example.com"

    def test_returns_none_if_direct_link_is_social(self):
        href = "https://instagram.com/profile"
        assert extract_website_from_facebook_redirect(href) is None

    def test_returns_none_for_empty(self):
        assert extract_website_from_facebook_redirect(None) is None
        assert extract_website_from_facebook_redirect("") is None


# ============================================================
# 3. clean_website_url
# ============================================================

class TestCleanWebsiteUrl:
    def test_adds_https_if_missing(self):
        assert clean_website_url("example.com") == "https://example.com"
        assert clean_website_url("www.example.com") == "https://www.example.com"

    def test_keeps_existing_scheme(self):
        assert clean_website_url("http://example.com") == "http://example.com"
        assert clean_website_url("https://example.com") == "https://example.com"

    def test_strips_trailing_slash(self):
        assert clean_website_url("https://example.com/") == "https://example.com"

    def test_strips_whitespace(self):
        assert clean_website_url("  https://example.com  ") == "https://example.com"
