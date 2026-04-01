import sqlite3
import logging
from pathlib import Path

DB_PATH = Path("seen_listings.db")
logger = logging.getLogger(__name__)


def init_db():
    """Create tables if they don't exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_listings (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bot_state (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
        """)
        # Default: alerts enabled
        conn.execute("""
            INSERT OR IGNORE INTO bot_state (key, value) VALUES ('alerts_enabled', '1')
        """)
        conn.commit()
    logger.info("Database initialised.")


def is_seen(listing_id: str) -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM seen_listings WHERE id = ?", (listing_id,)
        ).fetchone()
    return row is not None


def mark_seen(listing_id: str, source: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO seen_listings (id, source) VALUES (?, ?)",
            (listing_id, source),
        )
        conn.commit()


def get_alerts_enabled() -> bool:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT value FROM bot_state WHERE key = 'alerts_enabled'"
        ).fetchone()
    return row[0] == "1" if row else True


def set_alerts_enabled(enabled: bool):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO bot_state (key, value) VALUES ('alerts_enabled', ?)",
            ("1" if enabled else "0"),
        )
        conn.commit()
