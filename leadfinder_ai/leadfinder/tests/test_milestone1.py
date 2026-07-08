"""Milestone 1 tests – Project setup, configuration, logging, database, CLI scaffold.

Tests cover:
1. Settings  – default values, env-var override, type coercion.
2. Logger    – setup returns a Logger; no duplicate handlers.
3. Database  – table creation, insert, get, list, update (upsert), clear, delete.
4. Model     – BusinessLead validation and to_db_dict().
5. CLI       – typer app loads without error; search command is registered.
"""

import os
import sqlite3
import logging
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from leadfinder.config.settings import load_settings, Settings
from leadfinder.utils.logger import setup_logger
from leadfinder.database.db import DatabaseManager
from leadfinder.models.business import BusinessLead
from leadfinder.cli.main import app


# ============================================================
# 1. Settings Tests
# ============================================================

class TestSettings:
    def test_defaults(self):
        """Settings should have sensible defaults when nothing is configured."""
        cfg = load_settings(config_path="/nonexistent/path/config.json")
        assert cfg.db_path == "leadfinder.db"
        assert cfg.log_level == "INFO"
        assert cfg.rate_limit_delay == 1.5
        assert cfg.max_retries == 3
        assert cfg.playwright_headless is True
        assert cfg.request_timeout == 30_000

    def test_env_override_string(self, monkeypatch):
        """Environment variable should override the default db_path."""
        monkeypatch.setenv("LEADFINDER_DB_PATH", "/tmp/custom.db")
        cfg = load_settings()
        assert cfg.db_path == "/tmp/custom.db"

    def test_env_override_bool_true(self, monkeypatch):
        """Bool env var: 'false' string should produce False."""
        monkeypatch.setenv("LEADFINDER_PLAYWRIGHT_HEADLESS", "false")
        cfg = load_settings()
        assert cfg.playwright_headless is False

    def test_env_override_int(self, monkeypatch):
        """Integer env var should be correctly coerced."""
        monkeypatch.setenv("LEADFINDER_MAX_RETRIES", "5")
        cfg = load_settings()
        assert cfg.max_retries == 5

    def test_env_override_float(self, monkeypatch):
        """Float env var should be correctly coerced."""
        monkeypatch.setenv("LEADFINDER_RATE_LIMIT_DELAY", "2.5")
        cfg = load_settings()
        assert cfg.rate_limit_delay == 2.5

    def test_settings_is_pydantic_model(self):
        assert isinstance(load_settings(), Settings)

    def test_json_file_override(self, tmp_path):
        """Settings loaded from a JSON file should override defaults."""
        cfg_file = tmp_path / "config.json"
        cfg_file.write_text('{"log_level": "DEBUG", "max_retries": 7}')
        cfg = load_settings(config_path=str(cfg_file))
        assert cfg.log_level == "DEBUG"
        assert cfg.max_retries == 7


# ============================================================
# 2. Logger Tests
# ============================================================

class TestLogger:
    def test_returns_logger_instance(self, tmp_path):
        log = setup_logger(name="test_m1", log_file=str(tmp_path / "test.log"))
        assert isinstance(log, logging.Logger)

    def test_no_duplicate_handlers(self, tmp_path):
        """Calling setup_logger twice with the same name must not add duplicate handlers."""
        log_file = str(tmp_path / "dup.log")
        log1 = setup_logger(name="test_dup_m1", log_level="INFO", log_file=log_file)
        handler_count = len(log1.handlers)
        log2 = setup_logger(name="test_dup_m1", log_level="INFO", log_file=log_file)
        assert log1 is log2
        assert len(log2.handlers) == handler_count

    def test_log_level_applied(self, tmp_path):
        log = setup_logger(name="test_level_m1", log_level="DEBUG", log_file=str(tmp_path / "l.log"))
        assert log.level == logging.DEBUG

    def test_logger_has_handlers(self, tmp_path):
        log = setup_logger(name="test_handlers_m1", log_file=str(tmp_path / "h.log"))
        assert len(log.handlers) >= 1


# ============================================================
# 3. Database Tests
# ============================================================

class TestDatabaseManager:
    def test_db_file_created(self, tmp_db: DatabaseManager):
        import os
        assert os.path.exists(tmp_db.db_path)

    def test_table_exists(self, tmp_db: DatabaseManager):
        conn = sqlite3.connect(tmp_db.db_path)
        cur = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='businesses'"
        )
        assert cur.fetchone() is not None
        conn.close()

    def test_insert_returns_id(self, tmp_db: DatabaseManager, sample_lead: dict):
        row_id = tmp_db.insert_business(sample_lead)
        assert isinstance(row_id, int)
        assert row_id > 0

    def test_get_business(self, tmp_db: DatabaseManager, sample_lead: dict):
        row_id = tmp_db.insert_business(sample_lead)
        row = tmp_db.get_business(row_id)
        assert row is not None
        assert row["name"] == sample_lead["name"]

    def test_list_businesses(self, tmp_db: DatabaseManager, sample_lead: dict):
        tmp_db.insert_business(sample_lead)
        results = tmp_db.list_businesses()
        assert len(results) == 1
        assert results[0]["name"] == sample_lead["name"]

    def test_list_filter_by_country(self, tmp_db: DatabaseManager, sample_lead: dict):
        tmp_db.insert_business(sample_lead)
        results = tmp_db.list_businesses(country="US")
        assert len(results) == 0

    def test_upsert_updates_existing(self, tmp_db: DatabaseManager, sample_lead: dict):
        """Inserting the same name/country/keyword twice should update, not duplicate."""
        id1 = tmp_db.insert_business(sample_lead)
        updated = dict(sample_lead)
        updated["phone"] = "+10000000000"
        id2 = tmp_db.insert_business(updated)
        assert id1 == id2
        row = tmp_db.get_business(id1)
        assert row["phone"] == "+10000000000"

    def test_clear_all(self, tmp_db: DatabaseManager, sample_lead: dict):
        tmp_db.insert_business(sample_lead)
        deleted = tmp_db.clear_all()
        assert deleted == 1
        assert tmp_db.list_businesses() == []

    def test_delete_business(self, tmp_db: DatabaseManager, sample_lead: dict):
        row_id = tmp_db.insert_business(sample_lead)
        result = tmp_db.delete_business(row_id)
        assert result is True
        assert tmp_db.get_business(row_id) is None

    def test_delete_nonexistent(self, tmp_db: DatabaseManager):
        result = tmp_db.delete_business(9999)
        assert result is False

    def test_insert_requires_name(self, tmp_db: DatabaseManager):
        with pytest.raises(ValueError, match="'name' is required"):
            tmp_db.insert_business({"country": "India"})

    def test_whatsapp_stored_as_int(self, tmp_db: DatabaseManager, sample_lead: dict):
        """WhatsApp bool should be stored as int in SQLite."""
        row_id = tmp_db.insert_business(sample_lead)
        conn = sqlite3.connect(tmp_db.db_path)
        cur = conn.execute("SELECT whatsapp FROM businesses WHERE id = ?", (row_id,))
        raw = cur.fetchone()[0]
        conn.close()
        assert raw in (0, 1)


# ============================================================
# 4. Model Tests
# ============================================================

class TestBusinessLead:
    def test_valid_lead(self, sample_lead: dict):
        lead = BusinessLead(**sample_lead)
        assert lead.name == "Dream Home Realty"

    def test_score_range_upper(self):
        """Score must not exceed 100."""
        with pytest.raises(Exception):
            BusinessLead(name="X", score=101)

    def test_score_range_lower(self):
        """Score must not be negative."""
        with pytest.raises(Exception):
            BusinessLead(name="X", score=-1)

    def test_followers_non_negative(self):
        with pytest.raises(Exception):
            BusinessLead(name="X", followers=-5)

    def test_to_db_dict_excludes_id_and_created_at(self, sample_lead: dict):
        lead = BusinessLead(**sample_lead)
        d = lead.to_db_dict()
        assert "id" not in d
        assert "created_at" not in d
        assert "name" in d


# ============================================================
# 5. CLI Tests
# ============================================================

class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    def test_app_help(self):
        result = self.runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "leadfinder" in result.output.lower() or "LeadFinder" in result.output

    def test_search_command_registered(self):
        result = self.runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0
        assert "--country" in result.output
        assert "--keyword" in result.output

    def test_leads_command_registered(self):
        result = self.runner.invoke(app, ["leads", "--help"])
        assert result.exit_code == 0

    def test_search_missing_required_args(self):
        """search without --country and --keyword should fail."""
        result = self.runner.invoke(app, ["search"])
        assert result.exit_code != 0

    def test_search_runs_without_crash(self, tmp_path, monkeypatch):
        """search command should complete without unhandled exceptions.

        We mock search_meta_ads so the test validates CLI scaffold wiring
        without launching a real browser (that belongs to live integration tests).
        """
        monkeypatch.setenv("LEADFINDER_DB_PATH", str(tmp_path / "cli_test.db"))
        # Patch at the module level where the CLI imports it
        with patch("leadfinder.cli.main.search_meta_ads", return_value=[]), \
             patch("leadfinder.cli.main.DatabaseManager"):
            result = self.runner.invoke(
                app,
                ["search", "--country", "India", "--keyword", "Real Estate"],
            )
        # CLI should succeed (exit 0) — empty results is a valid outcome
        assert result.exit_code == 0
