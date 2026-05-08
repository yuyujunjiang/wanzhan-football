from __future__ import annotations

from typing import Any, Protocol


class ResultsProvider(Protocol):
    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        """
        Return a mapping keyed by `matchKey`, containing fields used by payout engine:
        - outcomeSPF: "胜" | "平" | "负"
        - outcomeRQSPF: "让胜" | "让平" | "让负"
        """

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        """Return deterministic match list for the given YYYY-MM-DD date string."""

