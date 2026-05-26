from __future__ import annotations

import datetime as dt
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from app.auth.deps import get_current_user
from app.domain.auth.models import UserOut
from app.domain.ledger.calculations import compute_estimated_payout, compute_stake
from app.domain.ledger.models import (
    LedgerTicketCreate,
    LedgerTicketOut,
    LedgerTicketSettledUpdate,
    LedgerTicketUpdate,
)
from app.domain.ledger.pending_settlement import settle_pending_tickets
from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.results.factory import get_results_provider
from app.storage.ledger_store import LedgerStore

router = APIRouter(prefix="/api/ledger", tags=["ledger"])
logger = logging.getLogger(__name__)
store = LedgerStore()
_store_sqlite_path = os.environ.get("FC_SQLITE_PATH")


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
    user_id: str,
    results_by_match_key: dict[str, dict[str, Any]] | None = None,
) -> LedgerTicketOut:
    settlement = settle_ticket_if_ready(
        ticket,
        results_by_match_key if results_by_match_key is not None else _results_for_ticket(ticket),
    )
    if settlement is None:
        return ticket

    settled = _active_store().settle_ticket(
        user_id=user_id,
        ticket_id=ticket.id,
        actual_payout=settlement.actualPayout,
        profit=settlement.profit,
        leg_results=settlement.legResults,
    )
    return settled or ticket


def _settle_pending_tickets_best_effort(user_id: str) -> None:
    try:
        settle_pending_tickets(user_id)
    except Exception:
        logger.exception("failed to settle pending ledger tickets during read")


def _validate_unique_match_keys_legs(legs: list[Any]) -> None:
    seen: set[str] = set()
    for leg in legs:
        match_key = leg.matchKey if hasattr(leg, "matchKey") else leg["matchKey"]
        if match_key in seen:
            raise HTTPException(
                status_code=400,
                detail=f"duplicate matchKey is not allowed: {match_key}",
            )
        seen.add(match_key)


def _validate_unique_match_keys(payload: LedgerTicketCreate) -> None:
    _validate_unique_match_keys_legs(payload.legs)


@router.post("/tickets")
def create_ticket(
    payload: LedgerTicketCreate,
    user: UserOut = Depends(get_current_user),
) -> dict[str, Any]:
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
        user_id=user.id,
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
        ticket = _settle_created_ticket(ticket, user.id, results_by_match_key)
    return ticket.model_dump()


@router.post("/settle")
def settle_tickets(user: UserOut = Depends(get_current_user)) -> dict[str, int]:
    return {"settledCount": settle_pending_tickets(user.id)}


@router.get("/summary")
def summary(
    start: dt.date,
    end: dt.date,
    user: UserOut = Depends(get_current_user),
) -> dict[str, float | int]:
    _settle_pending_tickets_best_effort(user.id)
    return _active_store().summary(
        user_id=user.id,
        start=start.isoformat(),
        end=end.isoformat(),
    )


@router.get("/tickets")
def list_tickets(
    user: UserOut = Depends(get_current_user),
    date: dt.date | None = None,
    start: dt.date | None = None,
    end: dt.date | None = None,
    status: str = "all",
) -> list[dict[str, Any]]:
    if status not in {"all", "pending", "settled"}:
        raise HTTPException(status_code=400, detail="invalid status")

    _settle_pending_tickets_best_effort(user.id)
    tickets = _active_store().list_tickets(
        user_id=user.id,
        date=date.isoformat() if date is not None else None,
        start=start.isoformat() if start is not None else None,
        end=end.isoformat() if end is not None else None,
        status=status,
    )
    return [ticket.model_dump() for ticket in tickets]


@router.get("/tickets/{ticket_id}")
def get_ticket(
    ticket_id: str,
    user: UserOut = Depends(get_current_user),
) -> dict[str, Any]:
    _settle_pending_tickets_best_effort(user.id)
    ticket = _active_store().get_ticket(ticket_id, user.id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="not found")
    return ticket.model_dump()


@router.patch("/tickets/{ticket_id}")
async def patch_ticket(
    ticket_id: str,
    request: Request,
    user: UserOut = Depends(get_current_user),
    reSettle: bool = False,
) -> dict[str, Any]:
    ledger_store = _active_store()
    ticket = ledger_store.get_ticket(ticket_id, user.id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="not found")

    body = await request.json()
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="invalid body")

    if ticket.status == "pending":
        update = LedgerTicketUpdate.model_validate(body)
        _validate_unique_match_keys_legs(update.legs)
        updated = ledger_store.update_ticket_pending(
            user_id=user.id,
            ticket_id=ticket_id,
            date=update.date,
            multiplier=update.multiplier,
            legs=[leg.model_dump() for leg in update.legs],
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="not found")
        if reSettle:
            try:
                results_by_match_key = _results_for_match_keys(
                    [leg.matchKey for leg in updated.legs]
                )
            except Exception as exc:
                raise HTTPException(
                    status_code=503,
                    detail="results provider failed; ticket was not re-settled",
                ) from exc
            updated = _settle_created_ticket(updated, user.id, results_by_match_key)
        return updated.model_dump()

    if "legs" in body:
        raise HTTPException(status_code=400, detail="settled tickets cannot change legs")

    settled_update = LedgerTicketSettledUpdate.model_validate(body)
    updated = ledger_store.update_ticket_settled(
        user_id=user.id,
        ticket_id=ticket_id,
        stake=settled_update.stake,
        actual_payout=settled_update.actualPayout,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="not found")
    return updated.model_dump()


@router.delete("/tickets/{ticket_id}", status_code=204)
def delete_ticket(
    ticket_id: str,
    user: UserOut = Depends(get_current_user),
) -> Response:
    deleted = _active_store().delete_ticket(user_id=user.id, ticket_id=ticket_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="not found")
    return Response(status_code=204)
