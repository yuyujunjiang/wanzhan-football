from __future__ import annotations

import datetime as dt
import os
from typing import Any

from app.domain.ledger.models import LedgerTicketOut
from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.results.factory import get_results_provider
from app.storage.ledger_store import LedgerStore

_TZ = dt.timezone(dt.timedelta(hours=8))
_store_sqlite_path = os.environ.get("FC_SQLITE_PATH")
_store = LedgerStore()


def _active_store() -> LedgerStore:
    global _store, _store_sqlite_path

    sqlite_path = os.environ.get("FC_SQLITE_PATH")
    if sqlite_path != _store_sqlite_path:
        _store = LedgerStore()
        _store_sqlite_path = sqlite_path
    return _store


def _parse_kickoff_time(value: str | None) -> dt.datetime | None:
    if value is None:
        return None
    try:
        kickoff = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if kickoff.tzinfo is None:
        kickoff = kickoff.replace(tzinfo=_TZ)
    return kickoff


def _ticket_is_past_result_window(ticket: LedgerTicketOut) -> bool:
    latest_kickoff: dt.datetime | None = None
    for leg in ticket.legs:
        kickoff = _parse_kickoff_time(leg.kickoffTime)
        if kickoff is None:
            return False
        latest_kickoff = max(latest_kickoff, kickoff) if latest_kickoff else kickoff

    if latest_kickoff is None:
        return False
    return dt.datetime.now(_TZ) >= latest_kickoff + dt.timedelta(hours=4)


def _pending_tickets_for_settlement(user_id: str | None) -> list[tuple[str, LedgerTicketOut]]:
    ledger_store = _active_store()
    if user_id is not None:
        return [(user_id, ticket) for ticket in ledger_store.pending_tickets(user_id)]

    conn = ledger_store._get_conn()
    rows = conn.execute(
        "SELECT id, user_id FROM ledger_tickets WHERE status = 'pending' ORDER BY created_at DESC"
    ).fetchall()
    pairs: list[tuple[str, LedgerTicketOut]] = []
    for row in rows:
        ticket = ledger_store.get_ticket(row["id"], row["user_id"])
        if ticket is not None:
            pairs.append((row["user_id"], ticket))
    return pairs


def _results_for_match_keys(match_keys: list[str]) -> dict[str, dict[str, Any]]:
    return get_results_provider().get_results_by_match_keys(match_keys)


def _results_for_ticket(ticket: LedgerTicketOut) -> dict[str, dict[str, Any]]:
    return _results_for_match_keys([leg.matchKey for leg in ticket.legs])


def settle_pending_tickets(user_id: str | None = None) -> int:
    settled_count = 0
    ledger_store = _active_store()
    for owner_id, ticket in _pending_tickets_for_settlement(user_id):
        if not _ticket_is_past_result_window(ticket):
            continue

        settlement = settle_ticket_if_ready(ticket, _results_for_ticket(ticket))
        if settlement is None:
            continue

        ledger_store.settle_ticket(
            user_id=owner_id,
            ticket_id=ticket.id,
            actual_payout=settlement.actualPayout,
            profit=settlement.profit,
            leg_results=settlement.legResults,
        )
        settled_count += 1
    return settled_count
