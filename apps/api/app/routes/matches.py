from __future__ import annotations

import datetime as dt

from fastapi import APIRouter

from app.domain.results.cache_io import build_empty_cache, read_cache
from app.domain.results.factory import get_results_provider

router = APIRouter(prefix="/api", tags=["matches"])


@router.get("/matches")
def list_matches(date: dt.date) -> list[dict]:
    provider = get_results_provider()
    return provider.list_matches(date=date.isoformat())


@router.get("/matches/cache")
def get_match_day_cache(date: dt.date) -> dict:
    """Return the raw per-day matches cache JSON (fixed + dynamic + meta)."""
    iso = date.isoformat()
    return read_cache(iso) or build_empty_cache(iso)


@router.get("/matches/range")
def list_matches_range(start: dt.date, days: int = 7) -> list[dict]:
    """
    Return a day-grouped schedule/results list.

    Response shape:
    [
      { "date": "YYYY-MM-DD", "matchCount": N, "matches": [ ... ] },
      ...
    ]
    """
    if days < 1 or days > 14:
        # keep it bounded for performance (sporttery provider hits upstream endpoints per day)
        return []

    provider = get_results_provider()
    out: list[dict] = []
    for i in range(days):
        d = (start + dt.timedelta(days=i)).isoformat()
        matches = provider.list_matches(date=d)
        out.append({"date": d, "matchCount": len(matches), "matches": matches})
    return out

