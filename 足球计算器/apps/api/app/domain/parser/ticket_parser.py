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
_ISSUE_RE = re.compile(r"第\s*(?P<issue>\d{7})\s*期")
_LEG_HEADER_RE = re.compile(
    r"第\s*(?P<idx>\d+)\s*场\s*(?P<week>周[一二三四五六日天]\d{3})\s*(?P<play>胜平负|让球胜平负)(?P<rest>.*)$"
)
_LEG_RE = re.compile(
    r"^(?P<match>.+?)\s+(?P<sel>让胜|让平|让负|胜|平|负)\s+(?P<sp>\d+(?:\.\d+)?)$"
)
_HANDICAP_RE = re.compile(r"(?P<handicap>[+-]?\d+(?:\.\d+)?)")
_TEAM_VS_RE = re.compile(r"(?P<home>[^\s]+)\s*(?:vs|VS|Vs|对阵|—|-)\s*(?P<away>[^\s]+)")
_SP_AT_RE = re.compile(r"(?P<sel>让胜|让平|让负|胜|平|负)\s*[@＠]?\s*(?P<sp>\d+(?:\.\d+)?)")


def _issue_to_date(issue7: str) -> str | None:
    # Observed format like 2605071 -> 2026-05-07 (take first 6 digits)
    if not re.fullmatch(r"\d{7}", issue7):
        return None
    yymmdd = issue7[:6]
    yy = int(yymmdd[:2])
    mm = int(yymmdd[2:4])
    dd = int(yymmdd[4:6])
    year = 2000 + yy
    try:
        return re.sub(
            r"^(\d{4})(\d{2})(\d{2})$",
            r"\1-\2-\3",
            f"{year:04d}{mm:02d}{dd:02d}",
        )
    except Exception:
        return None


def _parse_cn_handicap(rest: str) -> float | None:
    # Examples: "主队让1球" => -1, "主队受让1球" => +1
    m = re.search(r"(主队)?(受让|让)\s*(\d+(?:\.\d+)?)\s*球", rest)
    if not m:
        return None
    n = float(m.group(3))
    if m.group(2) == "受让":
        return n
    return -n


def parse_ticket(lines: list[OcrLine], source_images: list[str]) -> TicketDraft:
    warnings: list[str] = []

    play_type: PlayType | None = None
    multiplier: int | None = None
    pass_types: list[str] = []
    legs: list[LegDraft] = []
    pending_match_key: str | None = None
    pending_week: str | None = None
    pending_leg_play_type: PlayType | None = None
    pending_handicap: float | None = None
    ticket_date: str | None = None

    for line in lines:
        text = line.text.strip()
        if not text:
            continue

        if ticket_date is None:
            im = _ISSUE_RE.search(text)
            if im:
                ticket_date = _issue_to_date(im.group("issue"))

        hm = _LEG_HEADER_RE.search(text)
        if hm:
            pending_week = hm.group("week").strip()
            pending_leg_play_type = (
                PlayType.SPF if hm.group("play") == "胜平负" else PlayType.RQSPF
            )
            pending_handicap = _parse_cn_handicap(hm.group("rest") or "")
            if play_type is None and pending_leg_play_type is not None:
                play_type = pending_leg_play_type
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
            parts = []
            if ticket_date:
                parts.append(ticket_date)
            if pending_week:
                parts.append(pending_week)
            parts.append(f"{home} vs {away}")
            pending_match_key = " ".join(parts).strip()
            continue

        # More lenient leg parsing for real ticket OCR lines:
        # Try to find selection+SP pair and a reasonable matchKey (often contains "主队:... 客队:..." or "A vs B").
        spm = _SP_AT_RE.search(text)
        if spm:
            selection = spm.group("sel").strip()
            sp = float(spm.group("sp"))
            # strip common currency suffixes to keep float parse robust
            # (we already captured only the number, but OCR often keeps trailing "元" in the line)

            # matchKey: prefer previously captured team context, otherwise strip out the selection+sp fragment.
            match_key = pending_match_key
            if not match_key:
                match_key = text
                match_key = re.sub(re.escape(spm.group(0)), "", match_key).strip()
                match_key = re.sub(r"^(主队[:：])", "", match_key).strip()
                match_key = re.sub(r"(客队[:：])", " vs ", match_key).strip()
                match_key = re.sub(r"\\s+", " ", match_key).strip()

            handicap: float | None = None
            if pending_leg_play_type == PlayType.RQSPF and not selection.startswith("让"):
                # RQSPF票面有时写作「负@2.130」，但语义是「让负」
                if selection == "胜":
                    selection = "让胜"
                elif selection == "平":
                    selection = "让平"
                elif selection == "负":
                    selection = "让负"

            if selection.startswith("让"):
                if pending_handicap is not None:
                    handicap = pending_handicap
                else:
                    # Avoid accidentally capturing the year/date (e.g. 2026) from matchKey.
                    hm = re.search(r"(?P<handicap>[+-]\d+(?:\.\d+)?)", match_key or "")
                    if hm:
                        handicap = float(hm.group("handicap"))
            legs.append(LegDraft(matchKey=match_key or None, selection=selection, handicap=handicap, sp=sp))
            pending_match_key = None
            pending_week = None
            pending_leg_play_type = None
            pending_handicap = None

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
