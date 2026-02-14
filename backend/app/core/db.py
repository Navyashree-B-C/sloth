"""
SQLite persistence for wake history (EPIC 7).
Records session start/end for adaptation and analytics. Active sessions stay in-memory.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).resolve().parents[2] / "sloth_wake.db"
_conn: sqlite3.Connection | None = None


def _get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(str(_DB_PATH))
        _conn.execute(
            """
            CREATE TABLE IF NOT EXISTS wake_history (
                session_id TEXT PRIMARY KEY,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                released INTEGER NOT NULL DEFAULT 0,
                failed_attempts INTEGER NOT NULL DEFAULT 0,
                nudge_count INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        _conn.commit()
    return _conn


def record_session_start(
    session_id: str,
    failed_attempts: int = 0,
    nudge_count: int = 0,
) -> None:
    """Record that a session started. Called from create_session."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT OR REPLACE INTO wake_history (session_id, started_at, released, failed_attempts, nudge_count) VALUES (?, ?, 0, ?, ?)",
        (session_id, now, failed_attempts, nudge_count),
    )
    conn.commit()


def record_session_end(
    session_id: str,
    released: bool,
    failed_attempts: int = 0,
    nudge_count: int = 0,
) -> None:
    """Record that a session ended (release or abandon)."""
    conn = _get_conn()
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "UPDATE wake_history SET ended_at = ?, released = ?, failed_attempts = ?, nudge_count = ? WHERE session_id = ?",
        (now, 1 if released else 0, failed_attempts, nudge_count, session_id),
    )
    conn.commit()
