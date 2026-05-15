from __future__ import annotations

import sqlite3
import uuid
from typing import Any

from app.domain.ledger.calculations import (
    compute_estimated_payout,
    compute_profit,
    compute_stake,
    round2,
)
from app.domain.ledger.models import (
    LedgerLegInput,
    LedgerLegOut,
    LedgerStatus,
    LedgerTicketOut,
)

from .db import connect, migrate, now_epoch


class LedgerStore:
    def __init__(self) -> None:
        self._conn: sqlite3.Connection | None = None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = connect()
            migrate(self._conn)
        return self._conn

    def create_ticket(
        self,
        *,
        user_id: str,
        date: str,
        status: LedgerStatus,
        pass_type: str,
        multiplier: int,
        stake: float,
        estimated_payout: float,
        actual_payout: float,
        profit: float,
        legs: list[dict[str, Any]],
    ) -> LedgerTicketOut:
        ticket_id = uuid.uuid4().hex
        created_at = now_epoch()
        settled_at = created_at if status == "settled" else None
        validated_legs = [LedgerLegInput.model_validate(leg) for leg in legs]

        conn = self._get_conn()
        conn.execute(
            """
            INSERT INTO ledger_tickets(
                id, user_id, date, status, pass_type, multiplier, stake, estimated_payout,
                actual_payout, profit, created_at, settled_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id,
                user_id,
                date,
                status,
                pass_type,
                multiplier,
                round2(stake),
                round2(estimated_payout),
                round2(actual_payout),
                round2(profit),
                created_at,
                settled_at,
            ),
        )
        self._insert_legs(conn, ticket_id, validated_legs)
        conn.commit()
        created = self.get_ticket(ticket_id, user_id)
        if created is None:
            raise RuntimeError("created ledger ticket could not be loaded")
        return created

    def get_ticket(self, ticket_id: str, user_id: str) -> LedgerTicketOut | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT * FROM ledger_tickets WHERE id = ? AND user_id = ?",
            (ticket_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return self._ticket_from_row(row)

    def list_tickets(
        self,
        *,
        user_id: str,
        start: str | None = None,
        end: str | None = None,
        date: str | None = None,
        status: str = "all",
    ) -> list[LedgerTicketOut]:
        clauses: list[str] = ["user_id = ?"]
        params: list[Any] = [user_id]
        if date is not None:
            clauses.append("date = ?")
            params.append(date)
        if start is not None:
            clauses.append("date >= ?")
            params.append(start)
        if end is not None:
            clauses.append("date <= ?")
            params.append(end)
        if status != "all":
            clauses.append("status = ?")
            params.append(status)

        where = f" WHERE {' AND '.join(clauses)}"
        rows = self._get_conn().execute(
            f"SELECT * FROM ledger_tickets{where} ORDER BY created_at DESC",
            params,
        ).fetchall()
        return [self._ticket_from_row(row) for row in rows]

    def pending_tickets(self, user_id: str) -> list[LedgerTicketOut]:
        return self.list_tickets(user_id=user_id, status="pending")

    def settle_ticket(
        self,
        *,
        user_id: str,
        ticket_id: str,
        actual_payout: float,
        profit: float,
        leg_results: list[dict[str, Any]],
    ) -> LedgerTicketOut | None:
        conn = self._get_conn()
        cursor = conn.execute(
            """
            UPDATE ledger_tickets
            SET status = 'settled', actual_payout = ?, profit = ?, settled_at = ?
            WHERE id = ? AND user_id = ? AND status = 'pending'
            """,
            (round2(actual_payout), round2(profit), now_epoch(), ticket_id, user_id),
        )
        if cursor.rowcount == 0:
            conn.commit()
            return self.get_ticket(ticket_id, user_id)

        for result in leg_results:
            conn.execute(
                """
                UPDATE ledger_legs
                SET result_selection = ?, is_hit = ?
                WHERE id = ? AND ticket_id = ?
                """,
                (
                    result.get("resultSelection"),
                    self._bool_to_db(result.get("isHit")),
                    result.get("legId"),
                    ticket_id,
                ),
            )
        conn.commit()
        return self.get_ticket(ticket_id, user_id)

    def summary(self, *, user_id: str, start: str, end: str) -> dict[str, float | int]:
        row = self._get_conn().execute(
            """
            SELECT
                COALESCE(SUM(stake), 0) AS stake,
                COALESCE(
                    SUM(CASE WHEN status = 'settled' THEN actual_payout ELSE 0 END),
                    0
                ) AS payout,
                COALESCE(
                    SUM(CASE WHEN status = 'settled' THEN profit ELSE 0 END),
                    0
                ) AS profit,
                SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) AS pending_count,
                SUM(CASE WHEN status = 'settled' THEN 1 ELSE 0 END) AS settled_count,
                COUNT(*) AS ticket_count
            FROM ledger_tickets
            WHERE user_id = ? AND date >= ? AND date <= ?
            """,
            (user_id, start, end),
        ).fetchone()
        return {
            "stake": round2(float(row["stake"])),
            "payout": round2(float(row["payout"])),
            "profit": round2(float(row["profit"])),
            "pendingCount": int(row["pending_count"] or 0),
            "settledCount": int(row["settled_count"] or 0),
            "ticketCount": int(row["ticket_count"] or 0),
        }

    def delete_ticket(self, *, user_id: str, ticket_id: str) -> bool:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id FROM ledger_tickets WHERE id = ? AND user_id = ?",
            (ticket_id, user_id),
        ).fetchone()
        if row is None:
            return False
        conn.execute("DELETE FROM ledger_legs WHERE ticket_id = ?", (ticket_id,))
        cursor = conn.execute(
            "DELETE FROM ledger_tickets WHERE id = ? AND user_id = ?",
            (ticket_id, user_id),
        )
        conn.commit()
        return cursor.rowcount > 0

    def update_ticket_pending(
        self,
        *,
        user_id: str,
        ticket_id: str,
        date: str,
        multiplier: int,
        legs: list[dict[str, Any]],
    ) -> LedgerTicketOut | None:
        conn = self._get_conn()
        row = conn.execute(
            "SELECT id FROM ledger_tickets WHERE id = ? AND user_id = ? AND status = 'pending'",
            (ticket_id, user_id),
        ).fetchone()
        if row is None:
            return None

        validated_legs = [LedgerLegInput.model_validate(leg) for leg in legs]
        pass_type = f"{len(validated_legs)}x1"
        stake = compute_stake(multiplier=multiplier)
        estimated_payout = compute_estimated_payout(
            sp_values=[leg.sp for leg in validated_legs],
            multiplier=multiplier,
        )

        conn.execute("DELETE FROM ledger_legs WHERE ticket_id = ?", (ticket_id,))
        self._insert_legs(conn, ticket_id, validated_legs)
        conn.execute(
            """
            UPDATE ledger_tickets
            SET date = ?, pass_type = ?, multiplier = ?, stake = ?, estimated_payout = ?,
                actual_payout = 0, profit = 0, settled_at = NULL, status = 'pending'
            WHERE id = ? AND user_id = ?
            """,
            (
                date,
                pass_type,
                multiplier,
                stake,
                estimated_payout,
                ticket_id,
                user_id,
            ),
        )
        conn.commit()
        return self.get_ticket(ticket_id, user_id)

    def update_ticket_settled(
        self,
        *,
        user_id: str,
        ticket_id: str,
        stake: float,
        actual_payout: float,
    ) -> LedgerTicketOut | None:
        profit = compute_profit(actual_payout=actual_payout, stake=stake)
        conn = self._get_conn()
        cursor = conn.execute(
            """
            UPDATE ledger_tickets
            SET stake = ?, actual_payout = ?, profit = ?
            WHERE id = ? AND user_id = ? AND status = 'settled'
            """,
            (
                round2(stake),
                round2(actual_payout),
                profit,
                ticket_id,
                user_id,
            ),
        )
        conn.commit()
        if cursor.rowcount == 0:
            return None
        return self.get_ticket(ticket_id, user_id)

    def _insert_legs(
        self,
        conn: sqlite3.Connection,
        ticket_id: str,
        legs: list[LedgerLegInput],
    ) -> None:
        for leg in legs:
            conn.execute(
                """
                INSERT INTO ledger_legs(
                    ticket_id, match_key, match_id, league, home_team, away_team,
                    kickoff_time, play_type, selection, sp, handicap
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ticket_id,
                    leg.matchKey,
                    leg.matchId,
                    leg.league,
                    leg.homeTeam,
                    leg.awayTeam,
                    leg.kickoffTime,
                    leg.playType,
                    leg.selection,
                    leg.sp,
                    leg.handicap,
                ),
            )

    def _ticket_from_row(self, row: sqlite3.Row) -> LedgerTicketOut:
        return LedgerTicketOut(
            id=row["id"],
            date=row["date"],
            status=row["status"],
            passType=row["pass_type"],
            multiplier=int(row["multiplier"]),
            stake=float(row["stake"]),
            estimatedPayout=float(row["estimated_payout"]),
            actualPayout=float(row["actual_payout"]),
            profit=float(row["profit"]),
            createdAt=int(row["created_at"]),
            settledAt=int(row["settled_at"]) if row["settled_at"] is not None else None,
            legs=self._legs_for_ticket(row["id"]),
        )

    def _legs_for_ticket(self, ticket_id: str) -> list[LedgerLegOut]:
        rows = self._get_conn().execute(
            "SELECT * FROM ledger_legs WHERE ticket_id = ? ORDER BY id ASC",
            (ticket_id,),
        ).fetchall()
        return [
            LedgerLegOut(
                id=int(row["id"]),
                matchKey=row["match_key"],
                matchId=int(row["match_id"]) if row["match_id"] is not None else None,
                league=row["league"],
                homeTeam=row["home_team"],
                awayTeam=row["away_team"],
                kickoffTime=row["kickoff_time"],
                playType=row["play_type"],
                selection=row["selection"],
                sp=float(row["sp"]),
                handicap=float(row["handicap"]) if row["handicap"] is not None else None,
                resultSelection=row["result_selection"],
                isHit=bool(row["is_hit"]) if row["is_hit"] is not None else None,
            )
            for row in rows
        ]

    @staticmethod
    def _bool_to_db(value: Any) -> int | None:
        if value is None:
            return None
        return 1 if bool(value) else 0
