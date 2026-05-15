import importlib
import os
import uuid

from app.domain.auth.passwords import hash_password


def _store(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "ledger.sqlite3")
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    store_mod = importlib.import_module("app.storage.ledger_store")
    importlib.reload(store_mod)
    user_mod = importlib.import_module("app.storage.user_store")
    importlib.reload(user_mod)
    return store_mod.LedgerStore(), user_mod.UserStore()


def _user_id(user_store) -> str:
    user = user_store.create_user(
        username=f"ledger-test-{uuid.uuid4().hex[:8]}",
        password_hash=hash_password("pw"),
    )
    return user.id


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
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)

    ticket = store.create_ticket(
        user_id=user_id,
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

    loaded = store.get_ticket(ticket.id, user_id)
    assert loaded is not None
    assert loaded.id == ticket.id
    assert loaded.status == "pending"
    assert loaded.passType == "2x1"
    assert len(loaded.legs) == 2
    assert loaded.legs[1].playType == "RQSPF"


def test_get_ticket_returns_none_for_other_user(tmp_path):
    store, user_store = _store(tmp_path)
    user_a = _user_id(user_store)
    user_b = _user_id(user_store)

    ticket = store.create_ticket(
        user_id=user_a,
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

    assert store.get_ticket(ticket.id, user_b) is None


def test_summary_counts_pending_and_settled_tickets(tmp_path):
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)
    store.create_ticket(
        user_id=user_id,
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
        user_id=user_id,
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
        user_id=user_id,
        ticket_id=settled.id,
        actual_payout=36.0,
        profit=16.0,
        leg_results=[{"legId": settled.legs[0].id, "resultSelection": "胜", "isHit": True}],
    )

    summary = store.summary(user_id=user_id, start="2026-05-14", end="2026-05-14")
    assert summary["stake"] == 40.0
    assert summary["payout"] == 36.0
    assert summary["profit"] == 16.0
    assert summary["pendingCount"] == 1
    assert summary["settledCount"] == 1
    assert summary["ticketCount"] == 2


def test_settle_already_settled_ticket_does_not_overwrite_leg_results(tmp_path):
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)
    ticket = store.create_ticket(
        user_id=user_id,
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
    settled = store.settle_ticket(
        user_id=user_id,
        ticket_id=ticket.id,
        actual_payout=36.0,
        profit=16.0,
        leg_results=[{"legId": ticket.legs[0].id, "resultSelection": "胜", "isHit": True}],
    )
    assert settled is not None

    settled_again = store.settle_ticket(
        user_id=user_id,
        ticket_id=ticket.id,
        actual_payout=0.0,
        profit=-20.0,
        leg_results=[{"legId": ticket.legs[0].id, "resultSelection": "负", "isHit": False}],
    )

    assert settled_again is not None
    assert settled_again.legs[0].resultSelection == "胜"
    assert settled_again.legs[0].isHit is True


def test_delete_ticket_removes_ticket_and_legs(tmp_path):
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)
    ticket = store.create_ticket(
        user_id=user_id,
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

    assert store.delete_ticket(user_id=user_id, ticket_id=ticket.id) is True
    assert store.get_ticket(ticket.id, user_id) is None
    assert store.delete_ticket(user_id=user_id, ticket_id=ticket.id) is False


def test_update_ticket_pending_recomputes_stake_and_resets_settlement(tmp_path):
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)
    ticket = store.create_ticket(
        user_id=user_id,
        date="2026-05-14",
        status="pending",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(1, sp=1.8)],
    )
    store.settle_ticket(
        user_id=user_id,
        ticket_id=ticket.id,
        actual_payout=36.0,
        profit=16.0,
        leg_results=[{"legId": ticket.legs[0].id, "resultSelection": "胜", "isHit": True}],
    )

    updated = store.update_ticket_pending(
        user_id=user_id,
        ticket_id=ticket.id,
        date="2026-05-15",
        multiplier=5,
        legs=[_leg(1, sp=2.0), _leg(2, sp=1.5)],
    )

    assert updated is None

    pending = store.create_ticket(
        user_id=user_id,
        date="2026-05-14",
        status="pending",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=0.0,
        profit=0.0,
        legs=[_leg(3, sp=2.0)],
    )
    updated_pending = store.update_ticket_pending(
        user_id=user_id,
        ticket_id=pending.id,
        date="2026-05-15",
        multiplier=5,
        legs=[_leg(4, sp=2.0), _leg(5, sp=1.5)],
    )

    assert updated_pending is not None
    assert updated_pending.date == "2026-05-15"
    assert updated_pending.passType == "2x1"
    assert updated_pending.multiplier == 5
    assert updated_pending.stake == 10.0
    assert updated_pending.estimatedPayout == 30.0
    assert updated_pending.status == "pending"
    assert updated_pending.actualPayout == 0.0
    assert updated_pending.profit == 0.0
    assert updated_pending.settledAt is None
    assert len(updated_pending.legs) == 2
    assert updated_pending.legs[0].resultSelection is None
    assert updated_pending.legs[0].isHit is None


def test_update_ticket_settled_updates_profit(tmp_path):
    store, user_store = _store(tmp_path)
    user_id = _user_id(user_store)
    ticket = store.create_ticket(
        user_id=user_id,
        date="2026-05-14",
        status="settled",
        pass_type="1x1",
        multiplier=10,
        stake=20.0,
        estimated_payout=36.0,
        actual_payout=36.0,
        profit=16.0,
        legs=[_leg(1)],
    )

    updated = store.update_ticket_settled(
        user_id=user_id,
        ticket_id=ticket.id,
        stake=25.0,
        actual_payout=40.0,
    )

    assert updated is not None
    assert updated.stake == 25.0
    assert updated.actualPayout == 40.0
    assert updated.profit == 15.0
