from __future__ import annotations

import datetime as dt
import re
from typing import Any, Literal

MatchPhase = Literal["not_started", "live", "finished", "cancelled"]

_TZ = dt.timezone(dt.timedelta(hours=8))
# 竞彩：次日 08:00（含）前的场次归前一销售日；仅时间无时，需顺延到下一自然日。
_KICKOFF_EARLY_CUTOFF = dt.time(8, 0)
_CANCELLED_RE = re.compile(r"(取消|推迟|中断|腰斩|延期)")
_FINISHED_RE = re.compile(r"^(完|结束|终场|全场)")
_LIVE_STATUS_RE = re.compile(r"(进行|直播|上半场|下半场)")


def _today_iso(now: dt.datetime) -> str:
    return now.astimezone(_TZ).date().isoformat()


def _is_early_kickoff_time(t: dt.time) -> bool:
    return t <= _KICKOFF_EARLY_CUTOFF


def effective_kickoff_datetime(business_date: str, kickoff_time: str | None) -> dt.datetime | None:
    """
    Resolve real kickoff instant for a match listed under `business_date`.

    Sporttery often lists early-morning kickoffs (<=08:00) under the previous sales day
    with only HH:MM; those must map to the next calendar day.
    """
    if not kickoff_time:
        return None
    raw = kickoff_time.strip()
    if not raw:
        return None

    if re.match(r"^\d{4}-\d{2}-\d{2}", raw):
        try:
            parsed = dt.datetime.fromisoformat(raw)
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_TZ)
        return parsed.astimezone(_TZ)

    if not re.match(r"^\d{1,2}:\d{2}", raw):
        return None

    time_part = raw if len(raw) > 5 else f"{raw}:00"
    try:
        kickoff_t = dt.time.fromisoformat(time_part)
    except ValueError:
        return None
    try:
        sales_day = dt.date.fromisoformat(business_date)
    except ValueError:
        return None

    calendar_day = sales_day
    if _is_early_kickoff_time(kickoff_t):
        calendar_day = sales_day + dt.timedelta(days=1)

    return dt.datetime.combine(calendar_day, kickoff_t, tzinfo=_TZ)


def _parse_kickoff(date: str, kickoff_time: str | None) -> dt.datetime | None:
    return effective_kickoff_datetime(date, kickoff_time)


def compute_phase(match: dict[str, Any], *, now: dt.datetime | None = None) -> MatchPhase:
    now = now or dt.datetime.now(_TZ)
    status = str(match.get("matchStatus") or "")
    result_status = str(match.get("matchResultStatus") or "")
    blob = f"{status} {result_status}"

    if _CANCELLED_RE.search(blob):
        return "cancelled"

    final = match.get("finalScore")
    if final is not None and str(final).strip():
        return "finished"
    if _FINISHED_RE.search(status) or status.lower() in {"ft", "full", "end"}:
        return "finished"

    if _LIVE_STATUS_RE.search(status) or status.lower() in {"live", "playing"}:
        return "live"

    date = str(match.get("date") or "")
    if date == _today_iso(now):
        ko = _parse_kickoff(date, match.get("kickoffTime"))
        if ko is not None and now >= ko:
            return "live"

    return "not_started"


def apply_phase_for_today(
    matches: list[dict[str, Any]], *, date: str, now: dt.datetime | None = None
) -> list[dict[str, Any]]:
    now = now or dt.datetime.now(_TZ)
    if date != _today_iso(now):
        return matches
    return [{**m, "phase": compute_phase(m, now=now)} for m in matches]
