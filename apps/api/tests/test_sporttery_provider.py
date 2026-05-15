from app.domain.results.sporttery import SportteryResultsProvider


class _Response:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _Client:
    def get(self, url, params=None, headers=None):
        if "getMatchCalculatorV1" in url:
            return _Response({"value": {"matchInfoList": []}})
        return _Response(
            {
                "value": {
                    "matchResult": [
                        {
                            "a": "4.01",
                            "awayTeam": "圣何塞",
                            "d": "3.55",
                            "goalLine": "-1",
                            "h": "1.67",
                            "homeTeam": "西雅图",
                            "leagueNameAbbr": "美职",
                            "matchDate": "2026-05-14",
                            "matchId": 2039711,
                            "matchResultStatus": "2",
                            "poolStatus": "Payout",
                            "sectionsNo1": "1:1",
                            "sectionsNo999": "3:2",
                            "winFlag": "H",
                        }
                    ]
                }
            }
        )


def test_sporttery_uses_result_matches_when_calculator_has_no_history():
    provider = SportteryResultsProvider()
    provider._client = _Client()

    matches = provider.list_matches(date="2026-05-14")

    assert len(matches) == 1
    assert matches[0]["homeTeam"] == "西雅图"
    assert matches[0]["kickoffTime"] == ""
    assert matches[0]["finalScore"] == "3:2"
    assert matches[0]["outcomeSPF"] == "胜"
    assert matches[0]["outcomeRQSPF"] == "让平"
    assert matches[0]["had"]["h"] == "1.67"
    assert matches[0]["hhad"] is None
