from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any

from fastapi import APIRouter, HTTPException

from app.domain.ledger.calculations import compute_estimated_payout, compute_stake
from app.domain.ledger.models import LedgerTicketCreate, LedgerTicketOut
from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.results.factory import get_results_provider
from app.storage.ledger_store import LedgerStore

router = APIRouter(prefix="/api/ledger", tags=["ledger"])
logger = logging.getLogger(__name__)
store = LedgerStore()
_store_sqlite_path = os.environ.get("FC_SQLITE_PATH")
_TZ = dt.timezone(dt.timedelta(hours=8))


def _active_store() -> LedgerStore:
    global store, _store_sqlite_path

    sqlite_path = os.environ.get("FC_SQLITE_PATH")
    if sqlite_path != _store_sqlite_path:
        store = LedgerStore()
        _store_sqlite_path = sqlite_path
    return store


def _results_for_match_keys(match_keys: list[str]) -> dict[str, dict[str, Any]]:
    provider = get_results_provider()
    return provider.get_results_by_match_keys(match_keys)


def _results_for_ticket(ticket: LedgerTicketOut) -> dict[str, dict[str, Any]]:
    return _results_for_match_keys([leg.matchKey for leg in ticket.legs])


def _settle_created_ticket(
    ticket: LedgerTicketOut,
    results_by_match_key: dict[str, dict[str, Any]] | None = None,
) -> LedgerTicketOut:
    settlement = settle_ticket_if_ready(
        ticket,
        results_by_match_key if results_by_match_key is not None else _results_for_ticket(ticket),
    )
    if settlement is None:
        return ticket

    settled = _active_store().settle_ticket(
        ticket_id=ticket.id,
        actual_payout=settlement.actualPayout,
        profit=settlement.profit,
        leg_results=settlement.legResults,
    )
    return settled or ticket


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


def _settle_pending_tickets_best_effort() -> None:
    try:
        settle_pending_tickets()
    except Exception:
        logger.exception("failed to settle pending ledger tickets during read")


def settle_pending_tickets() -> int:
    settled_count = 0
    ledger_store = _active_store()
    for ticket in ledger_store.pending_tickets():
        if not _ticket_is_past_result_window(ticket):
            continue

        settlement = settle_ticket_if_ready(ticket, _results_for_ticket(ticket))
        if settlement is None:
            continue

        ledger_store.settle_ticket(
            ticket_id=ticket.id,
            actual_payout=settlement.actualPayout,
            profit=settlement.profit,
            leg_results=settlement.legResults,
        )
        settled_count += 1
    return settled_count


def _validate_unique_match_keys(payload: LedgerTicketCreate) -> None:
    seen: set[str] = set()
    for leg in payload.legs:
        if leg.matchKey in seen:
            raise HTTPException(
                status_code=400,
                detail=f"duplicate matchKey is not allowed: {leg.matchKey}",
            )
        seen.add(leg.matchKey)


@router.post("/tickets")
def create_ticket(payload: LedgerTicketCreate) -> dict[str, Any]:
    _validate_unique_match_keys(payload)

    results_by_match_key: dict[str, dict[str, Any]] | None = None
    if payload.mode == "results":
        try:
            results_by_match_key = _results_for_match_keys([leg.matchKey for leg in payload.legs])
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail="results provider failed; ticket was not created",
            ) from exc

    pass_type = f"{len(payload.legs)}x1"
    stake = compute_stake(multiplier=payload.multiplier)
    estimated_payout = compute_estimated_payout(
        sp_values=[leg.sp for leg in payload.legs],
        multiplier=payload.multiplier,
    )
    ticket = _active_store().create_ticket(
        date=payload.date,
        status="pending",
        pass_type=pass_type,
        multiplier=payload.multiplier,
        stake=stake,
        estimated_payout=estimated_payout,
        actual_payout=0.0,
        profit=0.0,
        legs=[leg.model_dump() for leg in payload.legs],
    )

    if payload.mode == "results":
        ticket = _settle_created_ticket(ticket, results_by_match_key)
    return ticket.model_dump()


@router.post("/settle")
def settle_tickets() -> dict[str, int]:
    return {"settledCount": settle_pending_tickets()}


@router.get("/summary")
def summary(start: dt.date, end: dt.date) -> dict[str, float | int]:
    _settle_pending_tickets_best_effort()
    return _active_store().summary(start=start.isoformat(), end=end.isoformat())


@router.get("/tickets")
def list_tickets(
    date: dt.date | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
    status: str = "all",
) -> list[dict[str, Any]]:
    if status not in {"all", "pending", "settled"}:
        raise HTTPException(status_code=400, detail="invalid status")

    _settle_pending_tickets_best_effort()
    tickets = _active_store().list_tickets(
        date=date.isoformat() if date is not None else None,
        start=start.isoformat() if start is not None else None,
        end=end.isoformat() if end is not None else None,
        status=status,
    )
    return [ticket.model_dump() for ticket in tickets]


@router.get("/tickets/{ticket_id}")
def get_ticket(ticket_id: str) -> dict[str, Any]:
    _settle_pending_tickets_best_effort()
    ticket = _active_store().get_ticket(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="not found")
    return ticket.model_dump()
