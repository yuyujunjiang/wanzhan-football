from __future__ import annotations

import datetime as dt
from typing import Any

import httpx

from .provider import ResultsProvider


class FootballDataOrgProvider(ResultsProvider):
    """
    Minimal provider backed by football-data.org (requires token).

    MVP scope:
    - list_matches(date): returns fixtures for a date (best-effort)
    - get_results_by_match_keys: NOT fully supported without a matchKey mapping strategy.
      For now we keep this provider mainly for the /api/matches page.
    """

    def __init__(self, *, token: str) -> None:
        self._token = token
        self._client = httpx.Client(
            base_url="https://api.football-data.org/v4",
            headers={"X-Auth-Token": token},
            timeout=15.0,
        )

    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        # We don't yet have a robust mapping from OCR-derived matchKey -> provider matchId.
        # Keep this empty so payout returns "partial" and user can still iterate on editing.
        return {}

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        d = dt.date.fromisoformat(date)
        resp = self._client.get("/matches", params={"dateFrom": d.isoformat(), "dateTo": d.isoformat()})
        resp.raise_for_status()
        data = resp.json()
        out: list[dict[str, Any]] = []
        for m in data.get("matches", []):
            home = m.get("homeTeam", {}).get("shortName") or m.get("homeTeam", {}).get("name")
            away = m.get("awayTeam", {}).get("shortName") or m.get("awayTeam", {}).get("name")
            league = m.get("competition", {}).get("code") or m.get("competition", {}).get("name")
            kickoff = m.get("utcDate")
            score = m.get("score", {}).get("fullTime", {}) or {}
            match_key = f"{date} {league} {home} vs {away}"
            out.append(
                {
                    "date": date,
                    "league": league,
                    "homeTeam": home,
                    "awayTeam": away,
                    "kickoffTime": kickoff,
                    "matchKey": match_key,
                    "score": score,
                }
            )
        return out

