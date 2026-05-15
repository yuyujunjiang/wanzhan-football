from __future__ import annotations

import sqlite3
from dataclasses import dataclass

from .db import connect, migrate, now_epoch


@dataclass(frozen=True)
class SessionOut:
    id: str
    user_id: str
    expires_at: int
    created_at: int


class SessionStore:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect()
            migrate(self._conn)
        return self._conn

    def create(self, session_id: str, user_id: str, expires_at: int) -> SessionOut:
        created_at = now_epoch()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO sessions(id, user_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
            (session_id, user_id, expires_at, created_at),
        )
        conn.commit()
        return SessionOut(
            id=session_id,
            user_id=user_id,
            expires_at=expires_at,
            created_at=created_at,
        )

    def get(self, session_id: str) -> SessionOut | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, user_id, expires_at, created_at FROM sessions WHERE id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return SessionOut(
            id=row["id"],
            user_id=row["user_id"],
            expires_at=int(row["expires_at"]),
            created_at=int(row["created_at"]),
        )

    def delete(self, session_id: str) -> None:
        conn = self._get_conn()
        conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        conn.commit()

    def delete_expired(self, now: int | None = None) -> int:
        cutoff = now if now is not None else now_epoch()
        conn = self._get_conn()
        cursor = conn.execute(
            "DELETE FROM sessions WHERE expires_at < ?",
            (cutoff,),
        )
        conn.commit()
        return cursor.rowcount
