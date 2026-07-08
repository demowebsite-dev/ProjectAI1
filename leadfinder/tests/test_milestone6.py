"""Milestone 6 tests – WhatsApp Detection.

Tests the `whatsapp.py` module for detecting WhatsApp contact methods
and extracting numbers from wa.me links.
"""

from __future__ import annotations

from leadfinder.parser.whatsapp import has_whatsapp, extract_whatsapp_number

# ============================================================
# 1. has_whatsapp
# ============================================================

class TestHasWhatsapp:
    def test_detects_wame_link(self):
        html = '<a href="https://wa.me/919382380980">Message us</a>'
        assert has_whatsapp(html) is True

    def test_detects_api_whatsapp(self):
        html = '<a href="https://api.whatsapp.com/send?phone=919382380980">WA</a>'
        assert has_whatsapp(html) is True

    def test_detects_web_whatsapp(self):
        html = 'https://web.whatsapp.com/send'
        assert has_whatsapp(html) is True

    def test_detects_text_chat_on_whatsapp(self):
        text = "Please Chat on WhatsApp for details"
        assert has_whatsapp(text) is True

    def test_detects_text_whatsapp_us(self):
        text = "WhatsApp us at 9382380980"
        assert has_whatsapp(text) is True

    def test_returns_false_if_absent(self):
        text = "Call us at 9382380980 or visit our website"
        assert has_whatsapp(text) is False

    def test_returns_false_for_empty(self):
        assert has_whatsapp("") is False
        assert has_whatsapp(None) is False

    def test_case_insensitive(self):
        text = "WHATSAPP US"
        assert has_whatsapp(text) is True


# ============================================================
# 2. extract_whatsapp_number
# ============================================================

class TestExtractWhatsappNumber:
    def test_extracts_number_from_wame(self):
        html = '<a href="https://wa.me/919382380980">Chat</a>'
        assert extract_whatsapp_number(html) == "919382380980"

    def test_extracts_with_plus(self):
        html = 'wa.me/+12025550123'
        assert extract_whatsapp_number(html) == "12025550123"

    def test_returns_none_if_no_number(self):
        assert extract_whatsapp_number("wa.me/text") is None

    def test_returns_none_if_no_wame(self):
        assert extract_whatsapp_number("api.whatsapp.com/send") is None
