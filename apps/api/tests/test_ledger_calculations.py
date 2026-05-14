from app.domain.ledger.calculations import (
    compute_estimated_payout,
    compute_profit,
    compute_stake,
)


def test_fixed_nx1_stake_is_two_yuan_times_multiplier():
    assert compute_stake(multiplier=1) == 2.0
    assert compute_stake(multiplier=50) == 100.0


def test_fixed_nx1_estimated_payout_multiplies_all_selected_odds():
    assert compute_estimated_payout(sp_values=[1.75, 1.67], multiplier=50) == 292.25


def test_profit_is_payout_minus_stake():
    assert compute_profit(actual_payout=292.25, stake=100.0) == 192.25
    assert compute_profit(actual_payout=0.0, stake=100.0) == -100.0
