from __future__ import annotations

import json
import sqlite3
import uuid
from dataclasses import dataclass
from typing import Any

from .db import connect, migrate, now_epoch


@dataclass(frozen=True)
class StoredTicket:
    id: str
    anonToken: str | None
    ticket: dict[str, Any]
    report: dict[str, Any] | None
    createdAt: int


class AnonymousTicketStore:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect()
            migrate(self._conn)
        return self._conn

    def create(
        self,
        *,
        ticket: dict[str, Any],
        report: dict[str, Any] | None,
        anon_token: str | None,
    ) -> str:
        ticket_id = uuid.uuid4().hex
        conn = self._get_conn()
        conn.execute(
            "INSERT INTO tickets(id, anon_token, ticket_json, report_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                ticket_id,
                anon_token,
                json.dumps(ticket, ensure_ascii=False),
                json.dumps(report, ensure_ascii=False) if report is not None else None,
                now_epoch(),
            ),
        )
        conn.commit()
        return ticket_id

    def get(self, ticket_id: str) -> StoredTicket | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id, anon_token, ticket_json, report_json, created_at FROM tickets WHERE id = ?",
            (ticket_id,),
        ).fetchone()
        if row is None:
            return None
        return StoredTicket(
            id=row["id"],
            anonToken=row["anon_token"],
            ticket=json.loads(row["ticket_json"]),
            report=json.loads(row["report_json"]) if row["report_json"] else None,
            createdAt=int(row["created_at"]),
        )

