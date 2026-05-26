from __future__ import annotations

from typing import Any

from app.domain.matches.phase import apply_phase_for_today, compute_phase
from app.domain.results.cache_io import merge_to_matches, read_cache
from app.domain.results.provider import ResultsProvider


class CacheOnlyMatchesProvider(ResultsProvider):
    """Read matches from local JSON only; never calls Sporttery."""

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        cache = read_cache(date)
        if not cache:
            return []
        matches = merge_to_matches(cache)
        enriched: list[dict[str, Any]] = []
        for m in matches:
            phase = m.get("phase") or compute_phase(m)
            enriched.append({**m, "phase": phase})
        return apply_phase_for_today(enriched, date=date)

    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        dates_seen: dict[str, list[dict[str, Any]]] = {}
        for key in match_keys:
            if len(key) < 10:
                continue
            date = key[:10]
            if date not in dates_seen:
                cache = read_cache(date)
                dates_seen[date] = merge_to_matches(cache) if cache else []
            for m in dates_seen[date]:
                if m.get("matchKey") != key:
                    continue
                payload: dict[str, Any] = {}
                for field in ("outcomeSPF", "outcomeRQSPF", "finalScore"):
                    val = m.get(field)
                    if val is not None:
                        payload[field] = val
                if payload:
                    out[key] = payload
                break
        return out
