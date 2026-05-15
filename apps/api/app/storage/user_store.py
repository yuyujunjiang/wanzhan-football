from __future__ import annotations

import sqlite3
import uuid
from dataclasses import dataclass

from app.domain.auth.models import UserOut

from .db import connect, migrate, now_epoch


def normalize_username(s: str) -> str:
    return s.strip().lower()


@dataclass(frozen=True)
class StoredUser:
    id: str
    username: str
    password_hash: str


class UserStore:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect()
            migrate(self._conn)
        return self._conn

    def create_user(self, *, username: str, password_hash: str) -> UserOut:
        user_id = uuid.uuid4().hex
        normalized = normalize_username(username)
        created_at = now_epoch()
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO users(id, username, password_hash, created_at) VALUES (?, ?, ?, ?)",
            (user_id, normalized, password_hash, created_at),
        )
        conn.commit()
        return UserOut(id=user_id, username=normalized)

    def get_by_username(self, username: str) -> StoredUser | None:
        normalized = normalize_username(username)
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?",
            (normalized,),
        ).fetchone()
        if row is None:
            return None
        return StoredUser(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
        )

    def get_by_id(self, user_id: str) -> UserOut | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, username FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            return None
        return UserOut(id=row["id"], username=row["username"])
