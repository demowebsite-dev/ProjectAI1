"""Milestone 5 tests – Phone Extraction.

Tests the `phone.py` parser, ensuring correct extraction from text,
normalisation to E.164 format, and validation logic.
"""

from __future__ import annotations

import pytest

from leadfinder.parser.phone import (
    extract_phones,
    normalize_phone,
    is_valid_phone,
    extract_first_phone,
)

# ============================================================
# 1. extract_phones
# ============================================================

class TestExtractPhones:
    def test_extracts_10_digit_number(self):
        text = "Call us at 9382380980 for more info."
        phones = extract_phones(text)
        assert "9382380980" in phones

    def test_extracts_with_plus_code(self):
        text = "Phone: +91-9382-380980"
        phones = extract_phones(text)
        assert "+91-9382-380980" in phones

    def test_extracts_us_format(self):
        text = "Contact: +1 (555) 123-4567 today."
        phones = extract_phones(text)
        assert "+1 (555) 123-4567" in phones

    def test_extracts_multiple(self):
        text = "Call 9876543210 or +15559998888"
        phones = extract_phones(text)
        assert "9876543210" in phones
        assert "+15559998888" in phones

    def test_ignores_too_short_numbers(self):
        text = "We have 5 items for $12 each."
        assert extract_phones(text) == []

    def test_handles_empty_string(self):
        assert extract_phones("") == []

    def test_handles_no_match(self):
        assert extract_phones("No numbers here whatsoever.") == []


# ============================================================
# 2. normalize_phone
# ============================================================

class TestNormalizePhone:
    def test_normalizes_indian_number(self):
        assert normalize_phone("+91 93823 80980") == "+919382380980"
        assert normalize_phone("9382380980", "IN") == "+919382380980"

    def test_normalizes_us_number(self):
        assert normalize_phone("+1 (202) 555-0123") == "+12025550123"
        assert normalize_phone("202-555-0123", "US") == "+12025550123"

    def test_returns_none_for_invalid(self):
        # 12345 is too short to be a valid phone number
        assert normalize_phone("12345", "IN") is None

    def test_returns_none_for_garbage(self):
        assert normalize_phone("not a number", "IN") is None


# ============================================================
# 3. is_valid_phone
# ============================================================

class TestIsValidPhone:
    def test_valid_indian_number(self):
        assert is_valid_phone("+919382380980") is True

    def test_valid_local_number(self):
        assert is_valid_phone("9382380980", "IN") is True

    def test_invalid_short_number(self):
        assert is_valid_phone("999", "IN") is False

    def test_invalid_chars(self):
        assert is_valid_phone("abcdef", "IN") is False


# ============================================================
# 4. extract_first_phone
# ============================================================

class TestExtractFirstPhone:
    def test_extracts_first_valid(self):
        text = "Invalid: 1234. Valid: 9382380980."
        assert extract_first_phone(text, "IN") == "+919382380980"

    def test_returns_none_if_no_valid(self):
        text = "No valid phones 1234 here."
        assert extract_first_phone(text, "IN") is None

    def test_extracts_international_priority(self):
        text = "Call us at +1 (202) 555-0123 or +919382380980"
        assert extract_first_phone(text, "IN") == "+12025550123"
