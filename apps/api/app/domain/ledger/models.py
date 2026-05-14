from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, Field

LedgerStatus = Literal["pending", "settled"]
LedgerMode = Literal["schedule", "results"]
LedgerPlayType = Literal["SPF", "RQSPF"]


class LedgerLegInput(BaseModel):
    matchKey: Annotated[str, Field(min_length=1)]
    matchId: int | None = None
    league: str
    homeTeam: str
    awayTeam: str
    kickoffTime: str | None = None
    playType: LedgerPlayType
    selection: str
    sp: Annotated[float, Field(gt=1.0, le=1000)]
    handicap: float | None = None


class LedgerTicketCreate(BaseModel):
    mode: LedgerMode
    date: Annotated[str, Field(pattern=r"^\d{4}-\d{2}-\d{2}$")]
    multiplier: Annotated[int, Field(ge=1, le=9999)]
    legs: Annotated[list[LedgerLegInput], Field(min_length=1)]


class LedgerLegOut(LedgerLegInput):
    id: int
    resultSelection: str | None = None
    isHit: bool | None = None


class LedgerTicketOut(BaseModel):
    id: str
    date: str
    status: LedgerStatus
    passType: str
    multiplier: int
    stake: float
    estimatedPayout: float
    actualPayout: float
    profit: float
    createdAt: int
    settledAt: int | None = None
    legs: list[LedgerLegOut]
