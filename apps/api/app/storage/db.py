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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at INTEGER NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            expires_at INTEGER NOT NULL,
            created_at INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON sessions(user_id)")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_tickets (
            id TEXT PRIMARY KEY,
            date TEXT NOT NULL,
            status TEXT NOT NULL,
            pass_type TEXT NOT NULL,
            multiplier INTEGER NOT NULL,
            stake REAL NOT NULL,
            estimated_payout REAL NOT NULL,
            actual_payout REAL NOT NULL,
            profit REAL NOT NULL,
            created_at INTEGER NOT NULL,
            settled_at INTEGER,
            user_id TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ledger_legs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticket_id TEXT NOT NULL,
            match_key TEXT NOT NULL,
            match_id INTEGER,
            league TEXT NOT NULL,
            home_team TEXT NOT NULL,
            away_team TEXT NOT NULL,
            kickoff_time TEXT,
            play_type TEXT NOT NULL,
            selection TEXT NOT NULL,
            sp REAL NOT NULL,
            handicap REAL,
            result_selection TEXT,
            is_hit INTEGER,
            FOREIGN KEY(ticket_id) REFERENCES ledger_tickets(id)
        )
        """
    )

    # Existing DBs without user_id: clear ledger per spec, then add column.
    ledger_cols = {row[1] for row in conn.execute("PRAGMA table_info(ledger_tickets)")}
    if "user_id" not in ledger_cols:
        conn.execute("DELETE FROM ledger_legs")
        conn.execute("DELETE FROM ledger_tickets")
        conn.execute("ALTER TABLE ledger_tickets ADD COLUMN user_id TEXT NOT NULL")

    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_tickets_date ON ledger_tickets(date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_tickets_status ON ledger_tickets(status)")
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_ledger_tickets_user_date ON ledger_tickets(user_id, date)"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_ledger_legs_ticket ON ledger_legs(ticket_id)")
    conn.commit()


def now_epoch() -> int:
    return int(time.time())
