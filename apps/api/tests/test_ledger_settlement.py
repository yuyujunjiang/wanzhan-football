from app.domain.ledger.settlement import settle_ticket_if_ready
from app.domain.ledger.models import LedgerTicketOut, LedgerLegOut


def _ticket(legs, estimated=63.0, stake=20.0):
    return LedgerTicketOut(
        id="ticket1",
        date="2026-05-14",
        status="pending",
        passType=f"{len(legs)}x1",
        multiplier=10,
        stake=stake,
        estimatedPayout=estimated,
        actualPayout=0.0,
        profit=0.0,
        createdAt=1,
        settledAt=None,
        legs=legs,
    )


def _leg(idx: int, play_type: str, selection: str):
    return LedgerLegOut(
        id=idx,
        matchKey=f"match-{idx}",
        matchId=idx,
        league="L",
        homeTeam="H",
        awayTeam="A",
        kickoffTime=None,
        playType=play_type,
        selection=selection,
        sp=1.5,
        handicap=None,
        resultSelection=None,
        isHit=None,
    )


def test_settlement_waits_when_any_result_is_missing():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "SPF", "平")])

    result = settle_ticket_if_ready(ticket, {"match-1": {"outcomeSPF": "胜"}})

    assert result is None


def test_fixed_nx1_wins_only_when_all_legs_hit():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "RQSPF", "让负")], estimated=52.5)

    result = settle_ticket_if_ready(
        ticket,
        {
            "match-1": {"outcomeSPF": "胜"},
            "match-2": {"outcomeRQSPF": "让负"},
        },
    )

    assert result is not None
    assert result.actualPayout == 52.5
    assert result.profit == 32.5
    assert [r["isHit"] for r in result.legResults] == [True, True]


def test_fixed_nx1_loses_when_one_leg_misses():
    ticket = _ticket([_leg(1, "SPF", "胜"), _leg(2, "RQSPF", "让负")], stake=20.0)

    result = settle_ticket_if_ready(
        ticket,
        {
            "match-1": {"outcomeSPF": "胜"},
            "match-2": {"outcomeRQSPF": "让胜"},
        },
    )

    assert result is not None
    assert result.actualPayout == 0.0
    assert result.profit == -20.0
    assert [r["isHit"] for r in result.legResults] == [True, False]
