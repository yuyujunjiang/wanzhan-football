from __future__ import annotations

import hashlib
from typing import Any

from .provider import ResultsProvider


def _stable_pick(key: str, choices: list[str]) -> str:
    digest = hashlib.md5(key.encode("utf-8")).digest()
    n = int.from_bytes(digest[:4], "big")
    return choices[n % len(choices)]


class MockResultsProvider(ResultsProvider):
    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        spf_choices = ["胜", "平", "负"]
        rqspf_choices = ["让胜", "让平", "让负"]

        out: dict[str, dict[str, Any]] = {}
        for k in match_keys:
            out[k] = {
                "outcomeSPF": _stable_pick(k, spf_choices),
                "outcomeRQSPF": _stable_pick(f"rq:{k}", rqspf_choices),
            }
        return out

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        # Deterministic tiny fixture list for MVP + tests.
        seeds = [
            ("EPL", "A", "B"),
            ("EPL", "C", "D"),
            ("LaLiga", "E", "F"),
        ]

        matches: list[dict[str, Any]] = []
        for idx, (league, home, away) in enumerate(seeds, start=1):
            match_key = f"{date} {league} {home} vs {away}"
            outcomes = self.get_results_by_match_keys([match_key])[match_key]
            matches.append(
                {
                    "date": date,
                    "league": league,
                    "homeTeam": home,
                    "awayTeam": away,
                    "kickoffTime": f"{date}T{(18 + idx):02d}:00:00",
                    "matchKey": match_key,
                    **outcomes,
                }
            )
        return matches

