from __future__ import annotations

from typing import Any

from fastapi import APIRouter, File, Header, HTTPException, UploadFile

from app.domain.ocr.ocr_service import StubOcrService
from app.domain.parser.ticket_parser import parse_ticket
from app.domain.results.mock_provider import MockResultsProvider
from app.domain.tickets.models import PayoutReport, Ticket, TicketDraft
from app.domain.tickets.payout import compute_payout
from app.domain.tickets.validate import TicketValidationError, validate_ticket
from app.storage.anonymous_store import AnonymousTicketStore

router = APIRouter(prefix="/api/tickets", tags=["tickets"])
store = AnonymousTicketStore()
results_provider = MockResultsProvider()


def _anon_token(
    *,
    anon_token_query: str | None = None,
    x_anon_token: str | None = Header(default=None, alias="X-Anon-Token"),
) -> str | None:
    return x_anon_token or anon_token_query


@router.post("/recognize")
def recognize_ticket(
    images: list[UploadFile] = File(...),
    anon_token_query: str | None = None,
    x_anon_token: str | None = Header(default=None, alias="X-Anon-Token"),
) -> dict[str, Any]:
    source_images = [img.filename or "unknown" for img in images]
    ocr = StubOcrService()
    lines = ocr.recognize(source_images=source_images)
    draft = parse_ticket(lines, source_images)
    ticket_id = store.create(
        ticket=draft.model_dump(),
        report=None,
        anon_token=_anon_token(anon_token_query=anon_token_query, x_anon_token=x_anon_token),
    )
    return {"id": ticket_id, **draft.model_dump()}


@router.post("/validate")
def validate(ticket: Ticket) -> dict[str, Any]:
    try:
        validate_ticket(ticket)
    except TicketValidationError as e:
        return {"ok": False, "errors": [str(e)]}
    return {"ok": True}


@router.post("/calculate")
def calculate(
    ticket: Ticket,
    anon_token_query: str | None = None,
    x_anon_token: str | None = Header(default=None, alias="X-Anon-Token"),
) -> dict[str, Any]:
    try:
        validate_ticket(ticket)
    except TicketValidationError as e:
        return {"ok": False, "errors": [str(e)]}

    results_by_match_key = results_provider.get_results_by_match_keys(
        [leg.matchKey for leg in ticket.legs]
    )
    report: PayoutReport = compute_payout(ticket, results_by_match_key)
    ticket_id = store.create(
        ticket=ticket.model_dump(),
        report=report.model_dump(),
        anon_token=_anon_token(anon_token_query=anon_token_query, x_anon_token=x_anon_token),
    )
    return {"id": ticket_id, "report": report.model_dump()}


@router.get("/{ticket_id}")
def get_ticket(ticket_id: str) -> dict[str, Any]:
    stored = store.get(ticket_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="not found")
    return {
        "id": stored.id,
        "anonToken": stored.anonToken,
        "ticket": stored.ticket,
        "report": stored.report,
        "createdAt": stored.createdAt,
    }

