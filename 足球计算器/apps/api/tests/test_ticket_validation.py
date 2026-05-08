import pytest
from pydantic import ValidationError

from app.domain.tickets.models import Leg, PlayType, Ticket
from app.domain.tickets.validate import TicketValidationError, validate_ticket


def _spf_ticket(**overrides) -> Ticket:
    base: dict = dict(
        playType=PlayType.SPF,
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            Leg(matchKey="2026-05-08 EPL A vs B", selection="胜", sp=1.85),
            Leg(matchKey="2026-05-08 EPL C vs D", selection="平", sp=2.10),
        ],
    )
    base.update(overrides)
    return Ticket(**base)


@pytest.mark.parametrize("bad_sp", [0.0, 1.0, -1.0])
def test_leg_model_rejects_bad_sp(bad_sp: float) -> None:
    with pytest.raises(ValidationError):
        Leg(matchKey="m1", selection="胜", sp=bad_sp)


def test_validate_ticket_requires_pass_types() -> None:
    with pytest.raises(ValidationError):
        _spf_ticket(passTypes=[])


def test_validate_ticket_requires_enough_legs_for_pass_types() -> None:
    ticket = _spf_ticket(
        passTypes=["3x1"],
        legs=[
            Leg(matchKey="m1", selection="胜", sp=1.5),
            Leg(matchKey="m2", selection="平", sp=2.0),
        ],
    )
    with pytest.raises(TicketValidationError):
        validate_ticket(ticket)


def test_validate_ticket_rqspf_requires_handicap_for_every_leg() -> None:
    ticket = Ticket(
        playType=PlayType.RQSPF,
        multiplier=1,
        passTypes=["2x1"],
        legs=[
            Leg(matchKey="m1", selection="让胜", handicap=-1, sp=2.0),
            Leg(matchKey="m2", selection="让平", sp=3.0),
        ],
    )
    with pytest.raises(TicketValidationError):
        validate_ticket(ticket)


def test_validate_ticket_passes_for_valid_spf_ticket() -> None:
    ticket = _spf_ticket()
    validate_ticket(ticket)


def test_validate_ticket_passes_for_valid_rqspf_ticket() -> None:
    ticket = Ticket(
        playType=PlayType.RQSPF,
        multiplier=2,
        passTypes=["2x1"],
        legs=[
            Leg(matchKey="m1", selection="让胜", handicap=-1, sp=2.0),
            Leg(matchKey="m2", selection="让平", handicap=0, sp=3.0),
        ],
    )
    validate_ticket(ticket)


def test_validate_ticket_passes_when_legs_exceed_pass_types_requirement() -> None:
    ticket = _spf_ticket(
        passTypes=["2x1"],
        legs=[
            Leg(matchKey="m1", selection="胜", sp=1.5),
            Leg(matchKey="m2", selection="平", sp=2.0),
            Leg(matchKey="m3", selection="负", sp=3.0),
        ],
    )
    validate_ticket(ticket)
