"""Configuration and settings management for LeadFinder AI.

Settings are loaded in priority order:
1. Default values (hardcoded in the model)
2. config.json file (if present)
3. Environment variables (highest priority)

Environment variable names follow the pattern LEADFINDER_<FIELD_NAME_UPPER>.
"""

import os
import json
import sys
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field


class Settings(BaseModel):
    """LeadFinder AI runtime settings."""

    # Database
    db_path: str = Field(default="leadfinder.db", description="Path to the SQLite database file")

    # Logging
    log_level: str = Field(default="INFO", description="Logging level: DEBUG, INFO, WARNING, ERROR")

    # Crawler behaviour
    rate_limit_delay: float = Field(
        default=1.5,
        ge=0.0,
        description="Minimum delay (seconds) between outbound requests to respect rate limits",
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        description="Maximum number of retry attempts for a failed request",
    )

    # Playwright
    playwright_headless: bool = Field(
        default=True, description="Run browser in headless mode (False = show browser window)"
    )
    request_timeout: int = Field(
        default=30_000,
        ge=1_000,
        description="Playwright navigation / selector timeout in milliseconds",
    )


# ---------------------------------------------------------------------------
# Environment-variable → field mapping
# ---------------------------------------------------------------------------
_ENV_MAP: dict[str, str] = {
    "LEADFINDER_DB_PATH": "db_path",
    "LEADFINDER_LOG_LEVEL": "log_level",
    "LEADFINDER_RATE_LIMIT_DELAY": "rate_limit_delay",
    "LEADFINDER_MAX_RETRIES": "max_retries",
    "LEADFINDER_PLAYWRIGHT_HEADLESS": "playwright_headless",
    "LEADFINDER_REQUEST_TIMEOUT": "request_timeout",
}


def load_settings(config_path: Optional[str] = None) -> Settings:
    """Load and merge settings from file + environment variables.

    Args:
        config_path: Optional explicit path to a JSON config file.
                     Falls back to ``LEADFINDER_CONFIG`` env var, then ``config.json``.

    Returns:
        A fully populated :class:`Settings` instance.
    """
    overrides: dict = {}

    # 1. JSON config file
    resolved_path = config_path or os.getenv("LEADFINDER_CONFIG", "config.json")
    cfg_file = Path(resolved_path)
    if cfg_file.exists():
        try:
            with open(cfg_file, encoding="utf-8") as fh:
                file_data = json.load(fh)
                overrides.update(file_data)
        except Exception as exc:  # noqa: BLE001
            print(f"Warning: Could not parse config file '{cfg_file}': {exc}", file=sys.stderr)

    # 2. Environment variables (highest priority)
    field_types: dict[str, type] = {
        name: info.annotation  # type: ignore[misc]
        for name, info in Settings.model_fields.items()
    }
    for env_key, field_name in _ENV_MAP.items():
        raw = os.getenv(env_key)
        if raw is None:
            continue
        ftype = field_types.get(field_name, str)
        if ftype is bool:
            overrides[field_name] = raw.strip().lower() in ("1", "true", "yes")
        elif ftype is int:
            try:
                overrides[field_name] = int(raw)
            except ValueError:
                print(f"Warning: Invalid int value for {env_key}={raw!r}", file=sys.stderr)
        elif ftype is float:
            try:
                overrides[field_name] = float(raw)
            except ValueError:
                print(f"Warning: Invalid float value for {env_key}={raw!r}", file=sys.stderr)
        else:
            overrides[field_name] = raw

    return Settings(**overrides)


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
settings: Settings = load_settings()
