from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.ledger.calculations import compute_profit
from app.domain.ledger.models import LedgerLegOut, LedgerTicketOut


@dataclass(frozen=True)
class SettlementResult:
    actualPayout: float
    profit: float
    legResults: list[dict[str, Any]]


def _result_for_leg(leg: LedgerLegOut, result: dict[str, Any]) -> str | None:
    if leg.playType == "SPF":
        return result.get("outcomeSPF")
    if leg.playType == "RQSPF":
        return result.get("outcomeRQSPF")
    return None


def settle_ticket_if_ready(
    ticket: LedgerTicketOut,
    results_by_match_key: dict[str, dict[str, Any]],
) -> SettlementResult | None:
    leg_results: list[dict[str, Any]] = []

    for leg in ticket.legs:
        match_result = results_by_match_key.get(leg.matchKey)
        if match_result is None:
            return None

        result_selection = _result_for_leg(leg, match_result)
        if result_selection is None:
            return None

        leg_results.append(
            {
                "legId": leg.id,
                "resultSelection": result_selection,
                "isHit": leg.selection == result_selection,
            }
        )

    all_hit = all(result["isHit"] for result in leg_results)
    actual_payout = ticket.estimatedPayout if all_hit else 0.0

    return SettlementResult(
        actualPayout=actual_payout,
        profit=compute_profit(actual_payout=actual_payout, stake=ticket.stake),
        legResults=leg_results,
    )
