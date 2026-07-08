"""Pytest shared fixtures for LeadFinder AI test suite."""

import os
import tempfile
import pytest

from leadfinder.database.db import DatabaseManager
from leadfinder.config.settings import load_settings


@pytest.fixture()
def tmp_db(tmp_path) -> DatabaseManager:
    """Return a DatabaseManager pointing at a fresh temporary SQLite database."""
    db_file = str(tmp_path / "test_leadfinder.db")
    return DatabaseManager(db_path=db_file)


@pytest.fixture()
def sample_lead() -> dict:
    """Return a minimal valid business lead dict for testing."""
    return {
        "name": "Dream Home Realty",
        "country": "India",
        "keyword": "Real Estate",
        "facebook": "https://facebook.com/dreamhomerealty",
        "followers": 9,
        "phone": "+919382380980",
        "whatsapp": True,
        "website": None,
        "score": 98,
    }
