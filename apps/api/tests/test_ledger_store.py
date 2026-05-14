import importlib
import os


def _store(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "ledger.sqlite3")
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    store_mod = importlib.import_module("app.storage.ledger_store")
    importlib.reload(store_mod)
    return store_mod.LedgerStore()


def _leg(match_id: int = 1, play_type: str = "SPF", selection: str = "胜", sp: float = 1.8):
    return {
        "matchKey": f"2026-05-14 League Home{match_id} vs Away{match_id}",
        "matchId": match_id,
        "league": "League",
        "homeTeam": f"Home{match_id}",
        "awayTeam": f"Away{match_id}",
        "kickoffTime": "2026-05-14T19:00:00",
        "playType": play_type,
        "selection": selection,
        "sp": sp,
        "handicap": None,
    }


def test_create_pending_ticket_round_trips_with_legs(tmp_path):
    store = _store(tmp_path)

    ticket = store.create_ticket(
        date="2026-05-14",
        status="pending",
        pass_type="2x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=63.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(1, "SPF", "胜", 1.5), _leg(2, "RQSPF", "让胜", 2.1)],
    )

    loaded = store.get_ticket(ticket.id)
    assert loaded is not None
    assert loaded.id == ticket.id
    assert loaded.status == "pending"
    assert loaded.passType == "2x1"
    assert len(loaded.legs) == 2
    assert loaded.legs[1].playType == "RQSPF"


def test_summary_counts_pending_and_settled_tickets(tmp_path):
    store = _store(tmp_path)
    store.create_ticket(
        date="2026-05-14",
        status="pending",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(1)],
    )
    settled = store.create_ticket(
        date="2026-05-14",
        status="settled",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=36.0,
        profit=16.0,
        legs=[_leg(2)],
    )
    store.settle_ticket(
        ticket_id=settled.id,
        actual_payout=36.0,
        profit=16.0,
        leg_results=[{"legId": settled.legs[0].id, "resultSelection": "胜", "isHit": True}],
    )

    summary = store.summary(start="2026-05-14", end="2026-05-14")
    assert summary["stake"] == 40.0
    assert summary["payout"] == 36.0
    assert summary["profit"] == 16.0
    assert summary["pendingCount"] == 1
    assert summary["settledCount"] == 1
    assert summary["ticketCount"] == 2
