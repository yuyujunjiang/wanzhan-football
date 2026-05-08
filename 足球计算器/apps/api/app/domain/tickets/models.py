from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, Field
from pydantic.types import StringConstraints


class PlayType(str, Enum):
    SPF = "SPF"
    RQSPF = "RQSPF"


class Leg(BaseModel):
    matchKey: Annotated[str, Field(min_length=1)]
    selection: str
    handicap: float | None = None
    sp: Annotated[float, Field(gt=1.0, le=1000)]


class Ticket(BaseModel):
    ticketType: Literal["jc-football"] = "jc-football"
    playType: PlayType
    multiplier: Annotated[int, Field(ge=1, le=9999)]
    passTypes: Annotated[
        list[Annotated[str, StringConstraints(pattern=r"^[2-9]\dx1$|^\d+x1$|^[2-9]x1$")]],
        Field(min_length=1),
    ]
    legs: Annotated[list[Leg], Field(min_length=1)]


class PayoutStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    PARTIAL = "partial"


class PayoutReport(BaseModel):
    status: PayoutStatus
    totalPayout: Annotated[float, Field(ge=0)]
    details: dict
    unmatchedLegs: list[str]
