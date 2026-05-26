from __future__ import annotations

import datetime as dt
import threading
from dataclasses import dataclass
from typing import Any

from app.domain.matches.phase import compute_phase

from .cache_io import (
    build_empty_cache,
    extract_dynamic_odds,
    extract_dynamic_results,
    extract_fixed,
    is_today,
    merge_dynamic_entry,
    merge_to_matches,
    now_iso,
    parse_dt,
    read_cache,
    write_cache,
)
from .provider import ResultsProvider
from .sporttery import SportteryResultsProvider


@dataclass(frozen=True)
class _RefreshPolicy:
    odds_ttl: dt.timedelta = dt.timedelta(minutes=30)
    results_ttl: dt.timedelta = dt.timedelta(minutes=5)


_policy = _RefreshPolicy()

_locks: dict[tuple[str, str], threading.Lock] = {}
_locks_guard = threading.Lock()


def _try_lock(date: str, kind: str) -> threading.Lock | None:
    with _locks_guard:
        lock = _locks.get((date, kind))
        if lock is None:
            lock = threading.Lock()
            _locks[(date, kind)] = lock
    if lock.acquire(blocking=False):
        return lock
    return None


def _dynamic_with_phase(m: dict[str, Any]) -> dict[str, Any]:
    odds = extract_dynamic_odds(m)
    results = extract_dynamic_results(m)
    merged = {**odds, **results}
    merged["phase"] = compute_phase(m)
    return merged


class CachedSportteryResultsProvider(ResultsProvider):
    """
    Writes Sporttery snapshots to local JSON. Used by matches-worker only.
    API reads via CacheOnlyMatchesProvider.
    """

    def __init__(self) -> None:
        self._upstream = SportteryResultsProvider()

    def refresh_matches(self, *, date: str) -> list[dict[str, Any]]:
        snapshot = self._upstream.list_matches(date=date)
        fixed = [extract_fixed(m) for m in snapshot]
        existing = read_cache(date)
        existing_by = (existing or {}).get("dynamic", {}).get("byMatchId") or {}
        by_mid: dict[str, dict[str, Any]] = {}
        for m in snapshot:
            mid = m.get("matchId")
            if mid is None:
                continue
            mid_s = str(mid)
            fresh = _dynamic_with_phase(m)
            by_mid[mid_s] = merge_dynamic_entry(
                existing_by.get(mid_s) if isinstance(existing_by.get(mid_s), dict) else None,
                fresh,
            )

        now = now_iso()
        cache = {
            "date": date,
            "fixed": fixed,
            "dynamic": {"fetchedAtOdds": now, "fetchedAtResults": now, "byMatchId": by_mid},
            "meta": {
                "createdAt": (existing or {}).get("meta", {}).get("createdAt") or now,
                "updatedAt": now,
            },
        }
        write_cache(date, cache)
        return merge_to_matches(cache)

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        cache = read_cache(date) or build_empty_cache(date)

        if not cache.get("fixed"):
            try:
                return self.refresh_matches(date=date)
            except Exception:
                return []

        if not is_today(date):
            return merge_to_matches(cache)

        dyn = cache.get("dynamic") or {}
        fetched_odds = parse_dt(dyn.get("fetchedAtOdds"))
        fetched_results = parse_dt(dyn.get("fetchedAtResults"))
        now_dt = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))

        need_odds = fetched_odds is None or (now_dt - fetched_odds) > _policy.odds_ttl
        need_results = fetched_results is None or (now_dt - fetched_results) > _policy.results_ttl

        if need_odds or need_results:
            try:
                return self.refresh_matches(date=date)
            except Exception:
                pass

        return merge_to_matches(cache)

    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        return self._upstream.get_results_by_match_keys(match_keys)
