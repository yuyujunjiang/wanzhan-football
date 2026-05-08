from __future__ import annotations

import re

from app.domain.ocr.ocr_service import OcrLine
from app.domain.tickets.models import LegDraft, PlayType, TicketDraft


_PLAY_TYPE_RE = re.compile(r"\b(SPF|RQSPF)\b")
_CN_PLAY_TYPE_RE = re.compile(r"(胜平负|让球胜平负)")
_MULTIPLIER_RE = re.compile(r"(?:倍(?:投)?)\s*([1-9]\d{0,3})")
_MULTIPLIER_CN_RE = re.compile(r"([1-9]\d{0,3})\s*倍")
_PASS_TYPE_RE = re.compile(r"\b(\d+x1)\b")
_PASS_TYPE_CN_RE = re.compile(r"(?:过关方式|串关)\s*([0-9]+[xX]1)", re.IGNORECASE)
_LEG_RE = re.compile(
    r"^(?P<match>.+?)\s+(?P<sel>让胜|让平|让负|胜|平|负)\s+(?P<sp>\d+(?:\.\d+)?)$"
)
_HANDICAP_RE = re.compile(r"(?P<handicap>[+-]?\d+(?:\.\d+)?)")
_TEAM_VS_RE = re.compile(r"(?P<home>[^\s]+)\s*(?:vs|VS|Vs|对阵|—|-)\s*(?P<away>[^\s]+)")
_SP_AT_RE = re.compile(r"(?P<sel>让胜|让平|让负|胜|平|负)\s*[@＠]?\s*(?P<sp>\d+(?:\.\d+)?)")


def parse_ticket(lines: list[OcrLine], source_images: list[str]) -> TicketDraft:
    warnings: list[str] = []

    play_type: PlayType | None = None
    multiplier: int | None = None
    pass_types: list[str] = []
    legs: list[LegDraft] = []
    pending_match_key: str | None = None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        if play_type is None:
            m = _PLAY_TYPE_RE.search(text)
            if m:
                play_type = PlayType(m.group(1))
            cm = _CN_PLAY_TYPE_RE.search(text)
            if cm:
                play_type = PlayType.SPF if cm.group(1) == "胜平负" else PlayType.RQSPF

        if multiplier is None:
            m = _MULTIPLIER_RE.search(text)
            if m:
                multiplier = int(m.group(1))
            cm = _MULTIPLIER_CN_RE.search(text)
            if cm:
                multiplier = int(cm.group(1))

        m = _PASS_TYPE_RE.search(text)
        if m:
            pt = m.group(1)
            if pt not in pass_types:
                pass_types.append(pt)
            continue
        cm = _PASS_TYPE_CN_RE.search(text)
        if cm:
            pt = cm.group(1).lower().replace("x", "x")
            pt = pt.replace("X", "x")
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
            continue

        # Team line context (often separated from SP line in OCR)
        # Examples:
        # - "主队: 阿斯顿维拉  Vs  客队: 诺丁汉森林"
        # - "阿斯顿维拉 vs 诺丁汉森林"
        team_text = text
        team_text = team_text.replace("主队", "").replace("客队", "")
        team_text = team_text.replace("：", ":")
        team_text = re.sub(r"\s*:\s*", " ", team_text)
        tv = _TEAM_VS_RE.search(team_text)
        if tv:
            home = tv.group("home").strip()
            away = tv.group("away").strip()
            pending_match_key = f"{home} vs {away}"
            continue

        # More lenient leg parsing for real ticket OCR lines:
        # Try to find selection+SP pair and a reasonable matchKey (often contains "主队:... 客队:..." or "A vs B").
        spm = _SP_AT_RE.search(text)
        if spm:
            selection = spm.group("sel").strip()
            sp = float(spm.group("sp"))
            # matchKey: prefer previously captured team context, otherwise strip out the selection+sp fragment.
            match_key = pending_match_key
            if not match_key:
                match_key = text
                match_key = re.sub(re.escape(spm.group(0)), "", match_key).strip()
                match_key = re.sub(r"^(主队[:：])", "", match_key).strip()
                match_key = re.sub(r"(客队[:：])", " vs ", match_key).strip()
                match_key = re.sub(r"\\s+", " ", match_key).strip()

            handicap: float | None = None
            if selection.startswith("让"):
                hm = _HANDICAP_RE.search(match_key)
                if hm:
                    handicap = float(hm.group("handicap"))
            legs.append(LegDraft(matchKey=match_key or None, selection=selection, handicap=handicap, sp=sp))
            pending_match_key = None

    if not legs:
        warnings.append("no_legs_parsed")
    if not pass_types:
        warnings.append("no_pass_types_parsed")
    if multiplier is None:
        warnings.append("no_multiplier_parsed")

    return TicketDraft(
        ticketType="jc-football",
        playType=play_type,
        multiplier=multiplier,
        passTypes=pass_types,
        legs=legs,
        warnings=warnings,
        sourceImages=source_images,
    )
