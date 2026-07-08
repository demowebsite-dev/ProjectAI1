"""SQLite database manager for LeadFinder AI.

Provides :class:`DatabaseManager` for CRUD operations on the ``businesses`` table.
All connections use ``row_factory = sqlite3.Row`` so results behave like dicts.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator, Optional

from leadfinder.config.settings import settings
from leadfinder.utils.logger import logger

# Column names that the database accepts (prevents SQL injection via key names)
_ALLOWED_COLUMNS: frozenset[str] = frozenset(
    {
        "name",
        "facebook",
        "instagram",
        "followers",
        "phone",
        "website",
        "whatsapp",
        "cta",
        "country",
        "keyword",
        "score",
    }
)


class DatabaseManager:
    """Manages connection and CRUD operations for the LeadFinder SQLite database."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        """Initialise the manager and create the schema if needed.

        Args:
            db_path: Path to the SQLite file.  Defaults to ``settings.db_path``.
        """
        self.db_path: str = db_path or settings.db_path
        self._ensure_directory()
        self._init_db()

    # ── Internals ───────────────────────────────────────────────────────────

    def _ensure_directory(self) -> None:
        """Create parent directories for the database file if they do not exist."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager that yields an open SQLite connection and commits on exit."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")  # Better concurrency
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Create the ``businesses`` table (and index) if they do not exist."""
        logger.debug("Initialising database at: %s", Path(self.db_path).resolve())
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS businesses (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    name        TEXT    NOT NULL,
                    facebook    TEXT,
                    instagram   TEXT,
                    followers   INTEGER,
                    phone       TEXT,
                    website     TEXT,
                    whatsapp    INTEGER,   -- stored as 0/1 (SQLite has no BOOLEAN)
                    cta         TEXT,
                    country     TEXT,
                    keyword     TEXT,
                    score       INTEGER,
                    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_businesses_name_country_keyword
                ON businesses (name, country, keyword)
                """
            )

    # ── Public API ──────────────────────────────────────────────────────────

    def insert_business(self, business_data: dict[str, Any]) -> int:
        """Insert a new business or update an existing one (upsert by name+country+keyword).

        Args:
            business_data: Dict with any subset of allowed column names.

        Returns:
            The ``id`` of the inserted or updated row.

        Raises:
            ValueError: If ``name`` is not provided in *business_data*.
        """
        filtered: dict[str, Any] = {
            k: v for k, v in business_data.items() if k in _ALLOWED_COLUMNS
        }
        if "name" not in filtered:
            raise ValueError("'name' is required when inserting a business.")

        # Normalise whatsapp to int for SQLite storage
        if "whatsapp" in filtered and isinstance(filtered["whatsapp"], bool):
            filtered["whatsapp"] = int(filtered["whatsapp"])

        with self._connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM businesses "
                "WHERE name = ? AND (country IS ? OR country = ?) AND (keyword IS ? OR keyword = ?)",
                (
                    filtered["name"],
                    filtered.get("country"),
                    filtered.get("country"),
                    filtered.get("keyword"),
                    filtered.get("keyword"),
                ),
            )
            row = cursor.fetchone()

            if row:
                business_id: int = row["id"]
                set_clause = ", ".join(f"{k} = ?" for k in filtered)
                conn.execute(
                    f"UPDATE businesses SET {set_clause} WHERE id = ?",
                    (*filtered.values(), business_id),
                )
                logger.info("Updated lead in DB: %s (id=%d)", filtered["name"], business_id)
                return business_id
            else:
                cols = ", ".join(filtered)
                placeholders = ", ".join("?" * len(filtered))
                cursor.execute(
                    f"INSERT INTO businesses ({cols}) VALUES ({placeholders})",
                    list(filtered.values()),
                )
                new_id: int = cursor.lastrowid  # type: ignore[assignment]
                logger.info("Inserted new lead into DB: %s (id=%d)", filtered["name"], new_id)
                return new_id

    def get_business(self, business_id: int) -> Optional[dict[str, Any]]:
        """Retrieve a business record by primary key.

        Args:
            business_id: The ``id`` of the business to retrieve.

        Returns:
            A dict representation of the row, or *None* if not found.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM businesses WHERE id = ?", (business_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def list_businesses(
        self,
        country: Optional[str] = None,
        keyword: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """Return all businesses, optionally filtered by country and/or keyword.

        Args:
            country: If provided, only returns rows matching this country.
            keyword: If provided, only returns rows matching this keyword.

        Returns:
            List of row dicts ordered by score DESC, created_at DESC.
        """
        query = "SELECT * FROM businesses"
        params: list[Any] = []
        conditions: list[str] = []

        if country:
            conditions.append("country = ?")
            params.append(country)
        if keyword:
            conditions.append("keyword = ?")
            params.append(keyword)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY score DESC, created_at DESC"

        with self._connection() as conn:
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def delete_business(self, business_id: int) -> bool:
        """Delete a business by primary key.

        Args:
            business_id: The ``id`` of the business to delete.

        Returns:
            *True* if a row was deleted, *False* if the id was not found.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                "DELETE FROM businesses WHERE id = ?", (business_id,)
            )
            deleted = cursor.rowcount > 0
            if deleted:
                logger.info("Deleted business id=%d from DB.", business_id)
            return deleted

    def clear_all(self) -> int:
        """Delete all rows from the businesses table.

        Returns:
            Number of rows deleted.

        Note:
            Primarily used in tests — use with caution in production.
        """
        with self._connection() as conn:
            cursor = conn.execute("DELETE FROM businesses")
            count: int = cursor.rowcount
            logger.warning("Cleared %d rows from businesses table.", count)
            return count
