from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

def _settings():
    from app.settings import settings

    return settings


def now_iso() -> str:
    return dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).isoformat()


def parse_dt(s: str | None) -> dt.datetime | None:
    if not s:
        return None
    try:
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None


def is_today(date: str) -> bool:
    try:
        d = dt.date.fromisoformat(date)
    except Exception:
        return False
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).date()
    return d == now


def cache_path(date: str) -> Path:
    return _settings().matches_cache_dir / f"{date}.json"


def read_cache(date: str) -> dict[str, Any] | None:
    path = cache_path(date)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def write_cache(date: str, payload: dict[str, Any]) -> None:
    path = cache_path(date)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_empty_cache(date: str) -> dict[str, Any]:
    now = now_iso()
    return {
        "date": date,
        "fixed": [],
        "dynamic": {"fetchedAtOdds": None, "fetchedAtResults": None, "byMatchId": {}},
        "meta": {"createdAt": now, "updatedAt": now},
    }


_ODDS_SNAPSHOT_KEY = "_oddsSnapshot"
_INTERNAL_DYNAMIC_KEYS = {_ODDS_SNAPSHOT_KEY}


def _had_has_values(had: Any) -> bool:
    if not isinstance(had, dict):
        return False
    return any(str(had.get(side) or "").strip() for side in ("h", "d", "a"))


def _hhad_has_values(hhad: Any) -> bool:
    if not isinstance(hhad, dict):
        return False
    return any(str(hhad.get(side) or "").strip() for side in ("h", "d", "a"))


def _public_dynamic(entry: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in entry.items() if k not in _INTERNAL_DYNAMIC_KEYS}


def merge_dynamic_entry(prev: dict[str, Any] | None, new: dict[str, Any]) -> dict[str, Any]:
    """
    Merge per-match dynamic fields when refreshing cache.

    赛果刷新会覆盖比分/赛果字段，但让球等赔率应从 JSON 里此前在售时写入的快照继承，
    不从赛果接口拉取。
    """
    prev = dict(prev or {})
    new = dict(new or {})

    snapshot: dict[str, Any] = dict(prev.get(_ODDS_SNAPSHOT_KEY) or {})
    if _hhad_has_values(new.get("hhad")):
        snapshot["hhad"] = new["hhad"]
    if _had_has_values(new.get("had")):
        snapshot["had"] = new["had"]

    merged: dict[str, Any] = {**prev, **new}
    merged[_ODDS_SNAPSHOT_KEY] = snapshot

    if not _hhad_has_values(merged.get("hhad")) and _hhad_has_values(snapshot.get("hhad")):
        merged["hhad"] = snapshot["hhad"]
    if not _had_has_values(merged.get("had")) and _had_has_values(snapshot.get("had")):
        merged["had"] = snapshot["had"]

  # goalLine: keep latest results goalLine, else from inherited hhad
    if not merged.get("goalLine"):
        hhad = merged.get("hhad")
        if isinstance(hhad, dict) and hhad.get("goalLine"):
            merged["goalLine"] = hhad.get("goalLine")

    return merged


def merge_to_matches(cache: dict[str, Any]) -> list[dict[str, Any]]:
    fixed = cache.get("fixed") or []
    dyn = (cache.get("dynamic") or {}).get("byMatchId") or {}
    out: list[dict[str, Any]] = []
    for f in fixed:
        mid = f.get("matchId")
        d = dyn.get(str(mid)) if mid is not None else None
        if isinstance(d, dict):
            out.append({**f, **_public_dynamic(d)})
        else:
            out.append({**f})
    return out


def extract_fixed(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "date": m.get("date"),
        "league": m.get("league"),
        "homeTeam": m.get("homeTeam"),
        "awayTeam": m.get("awayTeam"),
        "kickoffTime": m.get("kickoffTime"),
        "matchKey": m.get("matchKey"),
        "matchId": m.get("matchId"),
        "matchStatus": m.get("matchStatus"),
    }


def extract_dynamic_odds(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "had": m.get("had"),
        "hhad": m.get("hhad"),
        "goalLine": m.get("goalLine") or (m.get("hhad") or {}).get("goalLine"),
    }


def extract_dynamic_results(m: dict[str, Any]) -> dict[str, Any]:
    return {
        "finalScore": m.get("finalScore"),
        "halfScore": m.get("halfScore"),
        "goalLine": m.get("goalLine") or (m.get("hhad") or {}).get("goalLine"),
        "outcomeSPF": m.get("outcomeSPF"),
        "outcomeRQSPF": m.get("outcomeRQSPF"),
    }
