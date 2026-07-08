"""Milestone 8 tests – Lead Score.

Tests the `scorer.py` module to ensure it accurately calculates
the lead score based on the predefined rules.
"""

from __future__ import annotations

import pytest

from leadfinder.utils.scorer import calculate_score

class MockBusinessLead:
    def __init__(self, phone=None, whatsapp=False, followers=None, website=None):
        self.phone = phone
        self.whatsapp = whatsapp
        self.followers = followers
        self.website = website

class TestCalculateScore:
    def test_base_score_only(self):
        # Base score + no website (30) = 60
        lead = {"phone": None, "whatsapp": False, "followers": 5000, "website": None}
        assert calculate_score(lead) == 60

    def test_perfect_lead(self):
        # Base (30) + phone (20) + WA (20) + followers < 1000 (20) + no website (30) = 120 (clamped to 100)
        lead = {"phone": "+919382380980", "whatsapp": True, "followers": 500, "website": None}
        assert calculate_score(lead) == 100

    def test_worst_lead(self):
        # Base (30) + website (-20) = 10
        lead = {"phone": None, "whatsapp": False, "followers": 5000, "website": "https://example.com"}
        assert calculate_score(lead) == 10

    def test_mid_tier_lead(self):
        # Base (30) + phone (20) + website (-20) = 30
        lead = {"phone": "+919382380980", "whatsapp": False, "followers": 2000, "website": "https://example.com"}
        assert calculate_score(lead) == 30

    def test_works_with_model_instance(self):
        lead = MockBusinessLead(phone="+919382380980", whatsapp=True, followers=500, website=None)
        assert calculate_score(lead) == 100

    def test_followers_none_treated_as_greater_than_1000(self):
        # Base (30) + phone (20) + no website (30) = 80
        # followers=None means we don't know, so it doesn't get the < 1000 bonus
        lead = {"phone": "+1234567890", "whatsapp": False, "followers": None, "website": None}
        assert calculate_score(lead) == 80

    def test_clamped_minimum(self):
        # Base (30) + website exists (-20) = 10
        # Let's invent a scenario where score goes below 0 if we had more penalties.
        # But mathematically minimum is 30 - 20 = 10.
        # Just verifying it doesn't break.
        lead = {"phone": None, "whatsapp": False, "followers": 1500, "website": "https://example.com"}
        assert calculate_score(lead) == 10
