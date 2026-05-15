from __future__ import annotations

import datetime as dt
import re
from typing import Any

import httpx

from .provider import ResultsProvider

_SCORE_RE = re.compile(r"^\s*(\d+)\s*:\s*(\d+)\s*$")


def _parse_score(score: str | None) -> tuple[int, int] | None:
    if not score:
        return None
    m = _SCORE_RE.match(score)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _parse_handicap(goal_line: str | None) -> float | None:
    """
    sporttery uses goalLine like '+2' or '-1'. Interpreted as (home_score + goalLine) vs away_score.
    """
    if not goal_line:
        return None
    try:
        return float(goal_line)
    except ValueError:
        return None


def _outcome_spf_from_win_flag(win_flag: str | None) -> str | None:
    # Observed: 'H' | 'D' | 'A'
    if win_flag == "H":
        return "胜"
    if win_flag == "D":
        return "平"
    if win_flag == "A":
        return "负"
    return None


def _outcome_rqspf_from_score(home: int, away: int, handicap: float | None) -> str | None:
    if handicap is None:
        return None
    adj = home + handicap
    if adj > away:
        return "让胜"
    if adj == away:
        return "让平"
    return "让负"


def _normalize_match_key(s: str) -> str:
    return re.sub(r"\s+", "", s).strip().lower()


def _result_payload_from_sporttery_match(m: dict[str, Any]) -> dict[str, Any]:
    spf = _outcome_spf_from_win_flag(m.get("winFlag"))
    score = _parse_score(m.get("sectionsNo999"))
    handicap = _parse_handicap(m.get("goalLine"))
    rqspf = None
    if score:
        rqspf = _outcome_rqspf_from_score(score[0], score[1], handicap)

    payload: dict[str, Any] = {
        "finalScore": m.get("sectionsNo999") or None,
        "halfScore": m.get("sectionsNo1") or None,
        "goalLine": m.get("goalLine") or None,
        "matchResultStatus": m.get("matchResultStatus"),
        "poolStatus": m.get("poolStatus"),
    }
    if spf:
        payload["outcomeSPF"] = spf
    if rqspf:
        payload["outcomeRQSPF"] = rqspf
    return payload


def _match_from_result(date: str, m: dict[str, Any]) -> dict[str, Any]:
    league = m.get("leagueNameAbbr") or m.get("leagueName") or ""
    home = m.get("homeTeam") or m.get("allHomeTeam") or ""
    away = m.get("awayTeam") or m.get("allAwayTeam") or ""
    match_key = f"{date} {league} {home} vs {away}".strip()
    odds = {
        "h": m.get("h"),
        "d": m.get("d"),
        "a": m.get("a"),
    }
    return {
        "date": date,
        "league": league,
        "homeTeam": home,
        "awayTeam": away,
        # The result endpoint only exposes the match date, not kickoff time.
        # Keep this blank so the UI does not render a misleading 08:00.
        "kickoffTime": "",
        "matchKey": match_key,
        "matchId": m.get("matchId"),
        "matchStatus": m.get("matchResultStatus"),
        "had": odds,
        # The result endpoint only exposes one h/d/a odds set. Do not mirror it
        # into HHAD, otherwise handicap odds look valid when they are unknown.
        "hhad": None,
        **_result_payload_from_sporttery_match(m),
    }


class SportteryResultsProvider(ResultsProvider):
    """
    Provider backed by sporttery webapi endpoints used by m.sporttery.cn calculator/results pages.

    - Fixtures/odds (calculator): getMatchCalculatorV1.qry
    - Results (sgkj): getUniformMatchResultV1.qry
    """

    def __init__(self) -> None:
        self._client = httpx.Client(
            timeout=15.0,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://m.sporttery.cn/mjc/jsq/zqspf/index.html",
            },
        )

    def list_matches(self, *, date: str) -> list[dict[str, Any]]:
        # Calculator endpoint provides selling list with had/hhad odds.
        url = "https://webapi.sporttery.cn/gateway/uniform/football/getMatchCalculatorV1.qry"
        resp = self._client.get(url, params={"channel": "c", "poolCode": "hhad,had"})
        resp.raise_for_status()
        data = resp.json()
        out: list[dict[str, Any]] = []

        # Best-effort: also fetch results for the same date so the matches page can show赛果.
        results_by_match_id: dict[int, dict[str, Any]] = {}
        result_matches: list[dict[str, Any]] = []
        try:
            rurl = "https://webapi.sporttery.cn/gateway/uniform/football/getUniformMatchResultV1.qry"
            rresp = self._client.get(
                rurl,
                params={
                    "matchBeginDate": date,
                    "matchEndDate": date,
                    "leagueId": "",
                    "pageSize": "200",
                    "pageNo": "1",
                    "isFix": "0",
                    "matchPage": "1",
                    "pcOrWap": "1",
                },
                headers={"Referer": "https://www.sporttery.cn/jc/zqsgkj/"},
            )
            rresp.raise_for_status()
            rdata = rresp.json()
            for m in rdata.get("value", {}).get("matchResult") or []:
                mid = m.get("matchId")
                result_matches.append(_match_from_result(date, m))
                if isinstance(mid, int):
                    results_by_match_id[mid] = _result_payload_from_sporttery_match(m)
        except Exception:
            # No hard failure: keep list_matches usable even if results endpoint is flaky/blocked.
            results_by_match_id = {}

        for day in (data.get("value", {}).get("matchInfoList") or []):
            if day.get("businessDate") != date:
                continue
            for m in day.get("subMatchList") or []:
                league = m.get("leagueAbbName") or m.get("leagueAllName") or ""
                home = m.get("homeTeamAbbName") or m.get("homeTeamAllName") or ""
                away = m.get("awayTeamAbbName") or m.get("awayTeamAllName") or ""
                match_key = f"{date} {league} {home} vs {away}".strip()
                mid = m.get("matchId")
                result_payload = results_by_match_id.get(mid) if isinstance(mid, int) else None
                out.append(
                    {
                        "date": date,
                        "league": league,
                        "homeTeam": home,
                        "awayTeam": away,
                        "kickoffTime": m.get("matchTime"),
                        "matchKey": match_key,
                        "matchId": mid,
                        "matchStatus": m.get("matchStatus"),
                        "had": m.get("had"),
                        "hhad": m.get("hhad"),
                        **(result_payload or {}),
                    }
                )
        if not out and result_matches:
            return result_matches
        return out

    def get_results_by_match_keys(self, match_keys: list[str]) -> dict[str, dict[str, Any]]:
        # Group by date prefix to minimize requests.
        keys_by_date: dict[str, list[str]] = {}
        for k in match_keys:
            try:
                d = dt.date.fromisoformat(k[:10]).isoformat()
            except Exception:
                # unsupported matchKey format
                continue
            keys_by_date.setdefault(d, []).append(k)

        out: dict[str, dict[str, Any]] = {}
        for date, keys in keys_by_date.items():
            url = "https://webapi.sporttery.cn/gateway/uniform/football/getUniformMatchResultV1.qry"
            resp = self._client.get(
                url,
                params={
                    "matchBeginDate": date,
                    "matchEndDate": date,
                    "leagueId": "",
                    "pageSize": "200",
                    "pageNo": "1",
                    "isFix": "0",
                    "matchPage": "1",
                    "pcOrWap": "1",
                },
                headers={"Referer": "https://www.sporttery.cn/jc/zqsgkj/"},
            )
            resp.raise_for_status()
            data = resp.json()
            match_result = data.get("value", {}).get("matchResult") or []

            idx: dict[str, dict[str, Any]] = {}
            for m in match_result:
                league = m.get("leagueNameAbbr") or m.get("leagueName") or ""
                home = m.get("homeTeam") or m.get("allHomeTeam") or ""
                away = m.get("awayTeam") or m.get("allAwayTeam") or ""
                mk = f"{date} {league} {home} vs {away}".strip()
                idx[_normalize_match_key(mk)] = m

            for k in keys:
                m = idx.get(_normalize_match_key(k))
                if not m:
                    continue
                result_payload = _result_payload_from_sporttery_match(m)
                payload: dict[str, Any] = {}
                spf = result_payload.get("outcomeSPF")
                rqspf = result_payload.get("outcomeRQSPF")
                if spf:
                    payload["outcomeSPF"] = spf
                if rqspf:
                    payload["outcomeRQSPF"] = rqspf
                if payload:
                    out[k] = payload
        return out
