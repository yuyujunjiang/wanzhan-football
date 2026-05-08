from __future__ import annotations

import datetime as dt

from fastapi import APIRouter

from app.domain.results.mock_provider import MockResultsProvider

router = APIRouter(prefix="/api", tags=["matches"])
provider = MockResultsProvider()


@router.get("/matches")
def list_matches(date: dt.date) -> list[dict]:
    return provider.list_matches(date=date.isoformat())

