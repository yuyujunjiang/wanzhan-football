from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class PlayType(str, Enum):
    SPF = "SPF"
    RQSPF = "RQSPF"


class Leg(BaseModel):
    matchKey: str = Field(min_length=1)
    selection: str
    handicap: float | None = None
    sp: float = Field(gt=1.0, le=1000)


class Ticket(BaseModel):
    ticketType: Literal["jc-football"] = "jc-football"
    playType: PlayType
    multiplier: int = Field(ge=1, le=9999)
    passTypes: list[str] = Field(min_length=1)
    legs: list[Leg] = Field(min_length=1)


class PayoutStatus(str, Enum):
    WON = "won"
    LOST = "lost"
    PENDING = "pending"
    PARTIAL = "partial"


class PayoutReport(BaseModel):
    status: PayoutStatus
    totalPayout: float = Field(ge=0)
    details: dict
    unmatchedLegs: list[str]
