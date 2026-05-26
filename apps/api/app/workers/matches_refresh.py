from __future__ import annotations

import datetime as dt
import logging
import time

from app.domain.results.cached_sporttery import CachedSportteryResultsProvider
from app.domain.results.cache_io import is_today, parse_dt, read_cache
from app.settings import settings

logger = logging.getLogger(__name__)
_TZ = dt.timezone(dt.timedelta(hours=8))


def _today() -> dt.date:
    return dt.datetime.now(_TZ).date()


def _dates_full() -> list[str]:
    today = _today()
    dates: list[dt.date] = [today, today + dt.timedelta(days=1)]
    dates.extend(today - dt.timedelta(days=i) for i in range(1, 8))
    return [d.isoformat() for d in dates]


def _dates_fast() -> list[str]:
    return [_today().isoformat()]


def _should_refresh(date: str, kind: str) -> bool:
    if not is_today(date):
        return kind == "full"
    cache = read_cache(date)
    if not cache:
        return True
    dyn = cache.get("dynamic") or {}
    fetched = parse_dt(dyn.get("fetchedAtOdds" if kind == "odds" else "fetchedAtResults"))
    if fetched is None:
        return True
    now_dt = dt.datetime.now(_TZ)
    ttl = dt.timedelta(
        seconds=(
            settings.matches_worker_odds_ttl_seconds
            if kind == "odds"
            else settings.matches_worker_results_ttl_seconds
        )
    )
    return (now_dt - fetched) >= ttl


def _refresh_dates(dates: list[str], *, full_pass: bool) -> None:
    provider = CachedSportteryResultsProvider()
    for date in dates:
        try:
            if full_pass or not is_today(date):
                count = len(provider.refresh_matches(date=date))
                logger.info("refreshed matches date=%s count=%s", date, count)
                continue
            if _should_refresh(date, "odds") or _should_refresh(date, "results"):
                count = len(provider.refresh_matches(date=date))
                logger.info("refreshed matches date=%s count=%s", date, count)
        except Exception:
            logger.exception("failed to refresh matches date=%s", date)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    interval = max(60, settings.matches_worker_loop_seconds)
    full_interval = max(interval, settings.matches_worker_full_refresh_seconds)
    last_full: dt.datetime | None = None

    _refresh_dates(_dates_full(), full_pass=True)

    while True:
        now = dt.datetime.now(_TZ)
        if last_full is None or (now - last_full).total_seconds() >= full_interval:
            _refresh_dates(_dates_full(), full_pass=True)
            last_full = now
        else:
            _refresh_dates(_dates_fast(), full_pass=False)
        time.sleep(interval)


if __name__ == "__main__":
    main()
