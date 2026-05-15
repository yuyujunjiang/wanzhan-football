import sqlite3

from app.storage.db import migrate


def test_migrate_creates_users_sessions_and_ledger_user_id(tmp_path):
    path = tmp_path / "t.sqlite3"
    conn = sqlite3.connect(path)
    migrate(conn)
    tables = {
        row[0]
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }
    assert "users" in tables
    assert "sessions" in tables
    cols = [row[1] for row in conn.execute("PRAGMA table_info(ledger_tickets)")]
    assert "user_id" in cols
    conn.close()
