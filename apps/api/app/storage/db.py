from __future__ import annotations

import sqlite3
import time
from pathlib import Path


def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def connect() -> sqlite3.Connection:
    # Import inside function so tests can reload settings via env vars.
    from app.settings import settings

    path = settings.sqlite_path
    if str(path) != ":memory:":
        _ensure_parent_dir(path)
    conn = sqlite3.connect(str(path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def migrate(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tickets (
            id TEXT PRIMARY KEY,
            anon_token TEXT,
            ticket_json TEXT NOT NULL,
            report_json TEXT,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def now_epoch() -> int:
    return int(time.time())

