from app.domain.tickets.models import Ticket


def test_ticket_roundtrip():
    t = Ticket(
        playType="SPF",
        multiplier=2,
        passTypes=["2x1"],
        legs=[{"matchKey": "2026-05-08 EPL A vs B", "selection": "胜", "sp": 1.85}],
    )
    dumped = t.model_dump()
    loaded = Ticket.model_validate(dumped)
    assert loaded == t
