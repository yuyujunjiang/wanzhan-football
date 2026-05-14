from __future__ import annotations


def round2(value: float) -> float:
    return round(value + 1e-9, 2)


def compute_stake(*, multiplier: int) -> float:
    return round2(2.0 * multiplier)


def compute_estimated_payout(*, sp_values: list[float], multiplier: int) -> float:
    product = 1.0
    for sp in sp_values:
        product *= sp
    return round2(2.0 * multiplier * product)


def compute_profit(*, actual_payout: float, stake: float) -> float:
    return round2(actual_payout - stake)
