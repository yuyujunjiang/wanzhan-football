from __future__ import annotations

import datetime as dt
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.settings import settings

from .provider import ResultsProvider
from .sporttery import SportteryResultsProvider


def _now_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()


def _parse_dt(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def _is_today(date: str) -> bool:
    try:
        d = dt.date.fromisoformat(date)
    except Exception:
        return False
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    return d == now


@dataclass(frozen=True)
class _RefreshPolicy:
    odds_ttl: dt.timedelta = dt.timedelta(minutes=30)
    results_ttl: dt.timedelta = dt.timedelta(minutes=5)


_policy = _RefreshPolicy()

# In-process refresh locks. Keyed by (date, kind).
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


def _cache_path(date: str) -> Path:
    return settings.matches_cache_dir / f"{date}.json"


def _read_cache(date: str) -> dict[str, Any] | None:
    path = _cache_path(date)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_cache(date: str, payload: dict[str, Any]) -> None:
    path = _cache_path(date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _build_empty_cache(date: str) -> dict[str, Any]:
    now = _now_iso()
    return {
        "date": date,
        "fixed": [],
        "dynamic": {"fetchedAtOdds": None, "fetchedAtResults": None, "byMatchId": {}},
        "meta": {"createdAt": now, "updatedAt": now},
    }


def _merge_to_matches(cache: dict[str, Any]) -> list[dict[str, Any]]:
    fixed = cache.get("fixed") or []
    dyn = (cache.get("dynamic") or {}).get("byMatchId") or {}
    out: list[dict[str, Any]] = []
    for f in fixed:
        mid = f.get("matchId")
        d = dyn.get(str(mid)) if mid is not None else None
        if isinstance(d, dict):
            out.append({**f, **d})
        else:
            out.append({**f})
    return out


def _extract_fixed(m: dict[str, Any]) -> dict[str, Any]:
    # Keep only stable-ish fields for the list pages.
    return {
        "date": m.get("date"),
        "league": m.get("league"),
        "homeTeam": m.get("homeTeam"),
        "awayTeam": m.get("awayTeam"),
        "kickoffTime": m.get("kickoffTime"),
        "matchKey": m.get("matchKey"),
        "matchId": m.get("matchId"),
        "matchStatus": m.get("matchStatus"),
    }


def _extract_dynamic_odds(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "had": m.get("had"),
        "hhad": m.get("hhad"),
        "goalLine": m.get("goalLine") or (m.get("hhad") or {}).get("goalLine"),
    }


def _extract_dynamic_results(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "finalScore": m.get("finalScore"),
        "halfScore": m.get("halfScore"),
        "goalLine": m.get("goalLine") or (m.get("hhad") or {}).get("goalLine"),
        "outcomeSPF": m.get("outcomeSPF"),
        "outcomeRQSPF": m.get("outcomeRQSPF"),
    }


class CachedSportteryResultsProvider(ResultsProvider):
    """
    Cache sporttery schedule per-day to local JSON.

    - Non-today dates: cache-on-read (no periodic refresh)
    - Today: odds refresh every 30 minutes; results refresh every 5 minutes
    - In-process lock to avoid refresh storms for the same day/kind
    """

    def __init__(self) -> None:
        self._upstream = SportteryResultsProvider()

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        cache = _read_cache(date) or _build_empty_cache(date)

        # Bootstrap if empty: fetch full snapshot once.
        if not cache.get("fixed"):
            try:
                snapshot = self._upstream.list_matches(date=date)
                fixed = [_extract_fixed(m) for m in snapshot]
                by_mid: dict[str, dict[str, Any]] = {}
                for m in snapshot:
                    mid = m.get("matchId")
                    if mid is None:
                        continue
                    by_mid[str(mid)] = {**_extract_dynamic_odds(m), **_extract_dynamic_results(m)}
                now = _now_iso()
                cache = {
                    "date": date,
                    "fixed": fixed,
                    "dynamic": {"fetchedAtOdds": now, "fetchedAtResults": now, "byMatchId": by_mid},
                    "meta": {"createdAt": now, "updatedAt": now},
                }
                _write_cache(date, cache)
            except Exception:
                # If bootstrap fails and there was no cache, return empty.
                return []

        # For non-today: serve cached.
        if not _is_today(date):
            return _merge_to_matches(cache)

        # Today: refresh odds/results based on TTLs (best-effort) with per-kind locking.
        dyn = cache.get("dynamic") or {}
        fetched_odds = _parse_dt(dyn.get("fetchedAtOdds"))
        fetched_results = _parse_dt(dyn.get("fetchedAtResults"))
        now_dt = dt.datetime.now(dt.timezone(dt.timedelta(hours=8)))

        need_odds = fetched_odds is None or (now_dt - fetched_odds) > _policy.odds_ttl
        need_results = fetched_results is None or (now_dt - fetched_results) > _policy.results_ttl

        updated = False

        if need_odds:
            lock = _try_lock(date, "odds")
            if lock:
                try:
                    snapshot = self._upstream.list_matches(date=date)
                    fixed = [_extract_fixed(m) for m in snapshot]
                    by_mid = (dyn.get("byMatchId") or {}).copy()
                    for m in snapshot:
                        mid = m.get("matchId")
                        if mid is None:
                            continue
                        prev = by_mid.get(str(mid)) or {}
                        by_mid[str(mid)] = {**prev, **_extract_dynamic_odds(m)}
                    dyn["byMatchId"] = by_mid
                    dyn["fetchedAtOdds"] = _now_iso()
                    cache["fixed"] = fixed
                    cache["dynamic"] = dyn
                    cache["meta"]["updatedAt"] = _now_iso()
                    _write_cache(date, cache)
                    updated = True
                except Exception:
                    pass
                finally:
                    lock.release()

        if need_results:
            lock = _try_lock(date, "results")
            if lock:
                try:
                    snapshot = self._upstream.list_matches(date=date)
                    by_mid = (dyn.get("byMatchId") or {}).copy()
                    for m in snapshot:
                        mid = m.get("matchId")
                        if mid is None:
                            continue
                        prev = by_mid.get(str(mid)) or {}
                        by_mid[str(mid)] = {**prev, **_extract_dynamic_results(m)}
                    dyn["byMatchId"] = by_mid
                    dyn["fetchedAtResults"] = _now_iso()
                    cache["dynamic"] = dyn
                    cache["meta"]["updatedAt"] = _now_iso()
                    _write_cache(date, cache)
                    updated = True
                except Exception:
                    pass
                finally:
                    lock.release()

        if updated:
            cache = _read_cache(date) or cache

        return _merge_to_matches(cache)

    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        # Keep existing behavior for ticket settlement logic (no caching here yet).
        return self._upstream.get_results_by_match_keys(match_keys)

