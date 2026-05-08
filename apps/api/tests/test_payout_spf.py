from app.domain.tickets.models import Ticket
from app.domain.tickets.payout import compute_payout


def test_spf_two_legs_2x1_wins_payout_equals_prod_sp_times_2_times_multiplier() -> None:
    ticket = Ticket(
        playType="SPF",
        multiplier=2,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "胜", "sp": 1.5},
            {"matchKey": "m2", "selection": "负", "sp": 2.0},
        ],
    )
    results = {"m1": {"outcomeSPF": "胜"}, "m2": {"outcomeSPF": "负"}}
    report = compute_payout(ticket, results)

    assert report.status == "won"
    assert report.totalPayout == (1.5 * 2.0) * 2.0 * ticket.multiplier

