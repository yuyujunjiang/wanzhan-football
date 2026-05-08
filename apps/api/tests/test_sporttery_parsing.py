from app.domain.results.sporttery import (
    _outcome_rqspf_from_score,
    _outcome_spf_from_win_flag,
    _parse_handicap,
    _parse_score,
)


def test_parse_score():
    assert _parse_score("2:0") == (2, 0)
    assert _parse_score(" 0 : 1 ") == (0, 1)
    assert _parse_score("") is None
    assert _parse_score(None) is None
    assert _parse_score("x:y") is None


def test_parse_handicap():
    assert _parse_handicap("+2") == 2.0
    assert _parse_handicap("-1") == -1.0
    assert _parse_handicap(None) is None


def test_outcome_spf_from_win_flag():
    assert _outcome_spf_from_win_flag("H") == "胜"
    assert _outcome_spf_from_win_flag("D") == "平"
    assert _outcome_spf_from_win_flag("A") == "负"
    assert _outcome_spf_from_win_flag("") is None


def test_outcome_rqspf_from_score():
    # home -1 vs away: (2-1) > 0 => let win
    assert _outcome_rqspf_from_score(2, 0, -1) == "让胜"
    # home +1 vs away: (0+1) == 1 => let draw
    assert _outcome_rqspf_from_score(0, 1, +1) == "让平"
    # home +2 vs away: (0+2) > 1 => let win
    assert _outcome_rqspf_from_score(0, 1, +2) == "让胜"
    # home -1 vs away: (0-1) < 0 => let lose
    assert _outcome_rqspf_from_score(0, 0, -1) == "让负"

