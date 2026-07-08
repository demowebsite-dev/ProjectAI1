"""Centralised logging configuration for LeadFinder AI.

Provides a pre-configured :class:`logging.Logger` instance with:
- A Rich console handler for coloured, human-readable output.
- A rotating file handler writing to ``leadfinder.log``.

Usage::

    from leadfinder.utils.logger import logger
    logger.info("Hello from LeadFinder AI")
"""

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

# We import settings lazily to avoid circular imports during module load.
_LOG_FILE = "leadfinder.log"
_MAX_BYTES = 5 * 1024 * 1024   # 5 MB per file
_BACKUP_COUNT = 3


def setup_logger(
    name: str = "leadfinder",
    log_level: str | None = None,
    log_file: str | None = None,
) -> logging.Logger:
    """Create (or return existing) logger with Rich console + rotating file handlers.

    Args:
        name:      Logger name (defaults to ``leadfinder``).
        log_level: Override log level string (e.g. ``"DEBUG"``).
                   If *None* the value is read from :data:`leadfinder.config.settings.settings`.
        log_file:  Path to the log file.  Defaults to ``leadfinder.log`` in CWD.

    Returns:
        Configured :class:`logging.Logger` instance.
    """
    instance = logging.getLogger(name)

    # Guard against duplicate handler registration (e.g. during test reloads)
    if instance.handlers:
        return instance

    # Resolve log level
    if log_level is None:
        try:
            from leadfinder.config.settings import settings  # noqa: PLC0415
            log_level = settings.log_level
        except Exception:  # pragma: no cover
            log_level = "INFO"

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    instance.setLevel(numeric_level)

    # ── Rich console handler ────────────────────────────────────────────────
    rich_handler = RichHandler(
        level=numeric_level,
        rich_tracebacks=True,
        markup=True,
        show_time=True,
        show_path=False,
    )
    instance.addHandler(rich_handler)

    # ── Rotating file handler ───────────────────────────────────────────────
    resolved_file = log_file or _LOG_FILE
    try:
        Path(resolved_file).parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            resolved_file,
            maxBytes=_MAX_BYTES,
            backupCount=_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setLevel(logging.DEBUG)  # Always capture DEBUG in file
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        instance.addHandler(file_handler)
    except Exception as exc:  # noqa: BLE001
        print(f"Warning: Could not create file log handler: {exc}", file=sys.stderr)

    return instance


# ---------------------------------------------------------------------------
# Module-level singleton — import this everywhere
# ---------------------------------------------------------------------------
logger: logging.Logger = setup_logger()
