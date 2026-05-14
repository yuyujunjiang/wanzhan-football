from __future__ import annotations

from .models import PayoutReport, PayoutStatus, PlayType, Ticket
from .pass_types import combos


def _pick_from_pass_type(pass_type: str) -> int:
    left, _ = pass_type.split("x", 1)
    return int(left)


def compute_payout(ticket: Ticket, results_by_match_key: dict) -> PayoutReport:
    unmatched_legs: list[str] = []
    leg_hits: list[bool] = []

    for leg in ticket.legs:
        res = results_by_match_key.get(leg.matchKey)
        leg_play_type = leg.playType or ticket.playType
        if not res:
            unmatched_legs.append(leg.matchKey)
            leg_hits.append(False)
            continue

        if leg_play_type == PlayType.SPF:
            leg_hits.append(res.get("outcomeSPF") == leg.selection)
        elif leg_play_type == PlayType.RQSPF:
            leg_hits.append(res.get("outcomeRQSPF") == leg.selection)
        else:
            leg_hits.append(False)

    if unmatched_legs:
        return PayoutReport(
            status=PayoutStatus.PARTIAL,
            totalPayout=0.0,
            details={"legHits": leg_hits},
            unmatchedLegs=unmatched_legs,
        )

    total = 0.0
    leg_indexes = list(range(len(ticket.legs)))

    for pass_type in ticket.passTypes:
        pick = _pick_from_pass_type(pass_type)
        for c in combos(leg_indexes, pick):
            if not all(leg_hits[i] for i in c):
                continue

            sp_prod = 1.0
            for i in c:
                sp_prod *= ticket.legs[i].sp
            total += sp_prod * 2.0 * ticket.multiplier

    total_rounded = round(total, 2)
    return PayoutReport(
        status=PayoutStatus.WON if total_rounded > 0 else PayoutStatus.LOST,
        totalPayout=total_rounded,
        details={"legHits": leg_hits},
        unmatchedLegs=[],
    )
