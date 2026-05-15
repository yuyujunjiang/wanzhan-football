import importlib
import os

from app.domain.auth.passwords import hash_password


def _client(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "api.sqlite3")
    os.environ["FC_RESULTS_PROVIDER"] = "mock"
    os.environ["FC_MATCHES_SCHEDULER_ENABLED"] = "false"
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    user_mod = importlib.import_module("app.storage.user_store")
    importlib.reload(user_mod)
    session_mod = importlib.import_module("app.storage.session_store")
    importlib.reload(session_mod)
    auth_deps = importlib.import_module("app.auth.deps")
    importlib.reload(auth_deps)
    auth_routes = importlib.import_module("app.routes.auth")
    importlib.reload(auth_routes)
    ledger_routes = importlib.import_module("app.routes.ledger")
    importlib.reload(ledger_routes)
    main = importlib.import_module("app.main")
    importlib.reload(main)
    from fastapi.testclient import TestClient

    return TestClient(main.app), user_mod.UserStore()


def _login(client, user_store, username: str, password: str):
    user_store.create_user(username=username, password_hash=hash_password(password))
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200


def _two_user_clients(tmp_path):
    """Same DB file: two TestClient instances share cookies separately — use one client, switch users."""
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "api.sqlite3")
    os.environ["FC_RESULTS_PROVIDER"] = "mock"
    os.environ["FC_MATCHES_SCHEDULER_ENABLED"] = "false"
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    user_mod = importlib.import_module("app.storage.user_store")
    importlib.reload(user_mod)
    session_mod = importlib.import_module("app.storage.session_store")
    importlib.reload(session_mod)
    auth_deps = importlib.import_module("app.auth.deps")
    importlib.reload(auth_deps)
    auth_routes = importlib.import_module("app.routes.auth")
    importlib.reload(auth_routes)
    ledger_routes = importlib.import_module("app.routes.ledger")
    importlib.reload(ledger_routes)
    main = importlib.import_module("app.main")
    importlib.reload(main)
    from fastapi.testclient import TestClient

    store = user_mod.UserStore()
    store.create_user(username="alice", password_hash=hash_password("pw1"))
    store.create_user(username="bob", password_hash=hash_password("pw2"))
    return TestClient(main.app), TestClient(main.app)


def _payload():
    return {
        "mode": "schedule",
        "date": "2026-05-14",
        "multiplier": 10,
        "legs": [
            {
                "matchKey": "2026-05-14 EPL A vs B",
                "matchId": 1,
                "league": "EPL",
                "homeTeam": "A",
                "awayTeam": "B",
                "kickoffTime": "2026-05-14T19:00:00",
                "playType": "SPF",
                "selection": "平",
                "sp": 1.5,
                "handicap": None,
            },
        ],
    }


def test_user_b_cannot_get_user_a_ticket(tmp_path):
    alice, bob = _two_user_clients(tmp_path)
    alice.post("/api/auth/login", json={"username": "alice", "password": "pw1"})
    created = alice.post("/api/ledger/tickets", json=_payload()).json()

    bob.post("/api/auth/login", json={"username": "bob", "password": "pw2"})
    resp = bob.get(f"/api/ledger/tickets/{created['id']}")
    assert resp.status_code == 404


def test_delete_ticket_returns_204(tmp_path):
    client, store = _client(tmp_path)
    _login(client, store, "u1", "pw")
    tid = client.post("/api/ledger/tickets", json=_payload()).json()["id"]

    del_resp = client.delete(f"/api/ledger/tickets/{tid}")
    assert del_resp.status_code == 204

    get_resp = client.get(f"/api/ledger/tickets/{tid}")
    assert get_resp.status_code == 404


def test_patch_pending_updates_multiplier(tmp_path):
    client, store = _client(tmp_path)
    _login(client, store, "u1", "pw")
    tid = client.post("/api/ledger/tickets", json=_payload()).json()["id"]

    body = {
        "date": "2026-05-14",
        "multiplier": 20,
        "legs": _payload()["legs"],
    }
    resp = client.patch(f"/api/ledger/tickets/{tid}", json=body)
    assert resp.status_code == 200
    assert resp.json()["multiplier"] == 20
    assert resp.json()["stake"] == 40.0


def test_patch_settled_rejects_legs(tmp_path):
    client, store = _client(tmp_path)
    _login(client, store, "u1", "pw")
    payload = _payload()
    payload["mode"] = "results"
    tid = client.post("/api/ledger/tickets", json=payload).json()["id"]

    resp = client.patch(
        f"/api/ledger/tickets/{tid}",
        json={"stake": 10, "actualPayout": 30, "legs": _payload()["legs"]},
    )
    assert resp.status_code == 400
    assert "settled tickets cannot change legs" in resp.json()["detail"]


def test_patch_settled_updates_profit(tmp_path):
    client, store = _client(tmp_path)
    _login(client, store, "u1", "pw")
    payload = _payload()
    payload["mode"] = "results"
    tid = client.post("/api/ledger/tickets", json=payload).json()["id"]

    resp = client.patch(f"/api/ledger/tickets/{tid}", json={"stake": 10, "actualPayout": 25})
    assert resp.status_code == 200
    assert resp.json()["stake"] == 10.0
    assert resp.json()["actualPayout"] == 25.0
    assert resp.json()["profit"] == 15.0
