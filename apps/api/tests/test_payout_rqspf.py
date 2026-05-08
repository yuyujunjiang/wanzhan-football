from app.domain.tickets.models import Ticket
from app.domain.tickets.payout import compute_payout


def test_rqspf_uses_outcome_rqspf() -> None:
    ticket = Ticket(
        playType="RQSPF",
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            {"matchKey": "m1", "selection": "让胜", "handicap": -1, "sp": 2.1},
            {"matchKey": "m2", "selection": "让负", "handicap": 1, "sp": 1.7},
        ],
    )
    results = {"m1": {"outcomeRQSPF": "让胜"}, "m2": {"outcomeRQSPF": "让负"}}
    report = compute_payout(ticket, results)

    assert report.status == "won"
    assert report.totalPayout == (2.1 * 1.7) * 2.0 * ticket.multiplier

