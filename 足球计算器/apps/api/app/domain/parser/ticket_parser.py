from __future__ import annotations

import re

from app.domain.ocr.ocr_service import OcrLine
from app.domain.tickets.models import LegDraft, PlayType, TicketDraft


_PLAY_TYPE_RE = re.compile(r"\b(SPF|RQSPF)\b")
_MULTIPLIER_RE = re.compile(r"(?:倍(?:投)?)\s*([1-9]\d{0,3})")
_PASS_TYPE_RE = re.compile(r"\b(\d+x1)\b")
_LEG_RE = re.compile(
    r"^(?P<match>.+?)\s+(?P<sel>让胜|让平|让负|胜|平|负)\s+(?P<sp>\d+(?:\.\d+)?)$"
)
_HANDICAP_RE = re.compile(r"(?P<handicap>[+-]?\d+(?:\.\d+)?)")


def parse_ticket(lines: list[OcrLine], source_images: list[str]) -> TicketDraft:
    warnings: list[str] = []

    play_type: PlayType | None = None
    multiplier: int | None = None
    pass_types: list[str] = []
    legs: list[LegDraft] = []

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        if play_type is None:
            m = _PLAY_TYPE_RE.search(text)
            if m:
                play_type = PlayType(m.group(1))
                continue

        if multiplier is None:
            m = _MULTIPLIER_RE.search(text)
            if m:
                multiplier = int(m.group(1))
                continue

        m = _PASS_TYPE_RE.search(text)
        if m:
            pt = m.group(1)
            if pt not in pass_types:
                pass_types.append(pt)
            continue

        m = _LEG_RE.match(text)
        if m:
            match_key = m.group("match").strip()
            selection = m.group("sel").strip()
            sp = float(m.group("sp"))

            handicap: float | None = None
            if selection.startswith("让"):
                hm = _HANDICAP_RE.search(match_key)
                if hm:
                    handicap = float(hm.group("handicap"))
            legs.append(
                LegDraft(matchKey=match_key, selection=selection, handicap=handicap, sp=sp)
            )

    if not legs:
        warnings.append("no_legs_parsed")

    return TicketDraft(
        ticketType="jc-football",
        playType=play_type,
        multiplier=multiplier,
        passTypes=pass_types,
        legs=legs,
        warnings=warnings,
        sourceImages=source_images,
    )
