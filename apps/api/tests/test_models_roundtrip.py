import pytest

from app.domain.tickets.models import Ticket
from pydantic import ValidationError


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


def test_pass_types_enforces_pattern():
    # invalid format should fail validation (doesn't match the shared JSON schema pattern)
    with pytest.raises(ValidationError):
        Ticket(
            playType="SPF",
            multiplier=1,
            passTypes=["bad"],
            legs=[{"matchKey": "m1", "selection": "胜", "sp": 1.85}],
        )
