"""Business-level validation gate for a user-confirmed Ticket.

This module is the single entry point used by the calculate flow to ensure a
Ticket is structurally complete and self-consistent before any payout math
runs. Pydantic models stay deliberately permissive so all business-rule
failures surface from one place with a uniform error type.
"""

from __future__ import annotations

import re

from .models import PlayType, Ticket

_PASS_TYPE_RE = re.compile(r"^(?P<n>\d+)x(?P<m>\d+)$")


class TicketValidationError(ValueError):
    """Raised when a Ticket fails business-level validation."""


def _required_legs(pass_types: list[str]) -> int:
    max_n = 0
    for pt in pass_types:
        match = _PASS_TYPE_RE.match(pt)
        if not match:
            raise TicketValidationError(f"invalid passType format: {pt!r}")
        n = int(match.group("n"))
        if n < 1:
            raise TicketValidationError(f"invalid passType (N must be >= 1): {pt!r}")
        if n > max_n:
            max_n = n
    return max_n


def validate_ticket(ticket: Ticket) -> None:
    """Validate a user-confirmed ticket. Raise ``TicketValidationError`` on failure."""

    if not ticket.passTypes:
        raise TicketValidationError("passTypes is required")

    required = _required_legs(ticket.passTypes)
    if len(ticket.legs) < required:
        raise TicketValidationError(
            f"not enough legs for passTypes={ticket.passTypes}: "
            f"require >= {required}, got {len(ticket.legs)}"
        )

    for idx, leg in enumerate(ticket.legs):
        leg_play_type = leg.playType or ticket.playType
        if leg.sp is None or leg.sp <= 1.0:
            raise TicketValidationError(
                f"leg[{idx}] sp must be > 1.0, got {leg.sp!r}"
            )
        if leg_play_type == PlayType.RQSPF and leg.handicap is None:
            raise TicketValidationError(
                f"leg[{idx}] handicap is required for RQSPF"
            )
