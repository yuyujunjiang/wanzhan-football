from __future__ import annotations

from fastapi import APIRouter, File, UploadFile

from app.domain.ocr.ocr_service import StubOcrService
from app.domain.parser.ticket_parser import parse_ticket
from app.domain.tickets.models import TicketDraft

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


@router.post("/recognize", response_model=TicketDraft)
def recognize_ticket(images: list[UploadFile] = File(...)) -> TicketDraft:
    source_images = [img.filename or "unknown" for img in images]
    ocr = StubOcrService()
    lines = ocr.recognize(source_images=source_images)
    return parse_ticket(lines, source_images)

