from __future__ import annotations

import asyncio
import contextlib
import datetime as dt
import logging
from typing import Any

from app.settings import settings

from .factory import get_results_provider

logger = logging.getLogger(__name__)
_TZ = dt.timezone(dt.timedelta(hours=8))


def _today() -> dt.date:
    return dt.datetime.now(_TZ).date()


def _dates_to_refresh() -> list[str]:
    today = _today()
    dates: list[dt.date] = [today, today + dt.timedelta(days=1)]
    dates.extend(today - dt.timedelta(days=i) for i in range(1, 8))
    return [d.isoformat() for d in dates]


def _fast_dates_to_refresh() -> list[str]:
    return [_today().isoformat()]


def _refresh_date(provider: Any, date: str) -> int:
    refresh = getattr(provider, "refresh_matches", None)
    if callable(refresh):
        matches = refresh(date=date)
    else:
        matches = provider.list_matches(date=date)
    return len(matches or [])


async def _refresh_once(dates: list[str]) -> None:
    provider = get_results_provider()
    for date in dates:
        try:
            count = await asyncio.to_thread(_refresh_date, provider, date)
            logger.info("refreshed matches cache date=%s count=%s", date, count)
        except Exception:
            logger.exception("failed to refresh matches cache date=%s", date)


async def _matches_scheduler_loop() -> None:
    interval = max(60, settings.matches_scheduler_interval_seconds)
    full_interval = max(interval, settings.matches_scheduler_full_refresh_seconds)
    last_full_refresh: dt.datetime | None = None

    while True:
        now = dt.datetime.now(_TZ)
        if last_full_refresh is None or (now - last_full_refresh).total_seconds() >= full_interval:
            await _refresh_once(_dates_to_refresh())
            last_full_refresh = now
        else:
            await _refresh_once(_fast_dates_to_refresh())
        await asyncio.sleep(interval)


def start_matches_scheduler() -> asyncio.Task[None] | None:
    if not settings.matches_scheduler_enabled:
        return None
    return asyncio.create_task(_matches_scheduler_loop(), name="matches-cache-refresh")


async def stop_matches_scheduler(task: asyncio.Task[None] | None) -> None:
    if task is None:
        return
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
