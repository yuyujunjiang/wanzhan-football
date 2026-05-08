from __future__ import annotations

import datetime as dt

from fastapi import APIRouter

from app.domain.results.factory import get_results_provider

router = APIRouter(prefix="/api", tags=["matches"])


@router.get("/matches")
def list_matches(date: dt.date) -> list[dict]:
    provider = get_results_provider()
    return provider.list_matches(date=date.isoformat())

