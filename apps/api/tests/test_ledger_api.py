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


def _login(client, user_store, username: str = "ledgeruser", password: str = "secret123"):
    user_store.create_user(username=username, password_hash=hash_password(password))
    resp = client.post("/api/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text


def _payload(mode="schedule"):
    return {
        "mode": mode,
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
            {
                "matchKey": "2026-05-14 EPL C vs D",
                "matchId": 2,
                "league": "EPL",
                "homeTeam": "C",
                "awayTeam": "D",
                "kickoffTime": "2026-05-14T20:00:00",
                "playType": "RQSPF",
                "selection": "让平",
                "sp": 2.0,
                "handicap": None,
            },
        ],
    }


def test_create_schedule_ticket_returns_pending_ticket(tmp_path):
    client, user_store = _client(tmp_path)
    _login(client, user_store)

    resp = client.post("/api/ledger/tickets", json=_payload("schedule"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["passType"] == "2x1"
    assert body["stake"] == 20.0
    assert body["estimatedPayout"] == 60.0


def test_create_results_ticket_settles_immediately_with_mock_results(tmp_path):
    client, user_store = _client(tmp_path)
    _login(client, user_store)

    resp = client.post("/api/ledger/tickets", json=_payload("results"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "settled"
    assert body["actualPayout"] == 60.0
    assert body["profit"] == 40.0


def test_create_ticket_rejects_duplicate_match_keys_without_persisting(tmp_path):
    client, user_store = _client(tmp_path)
    _login(client, user_store)
    payload = _payload("schedule")
    payload["legs"][1]["matchKey"] = payload["legs"][0]["matchKey"]

    resp = client.post("/api/ledger/tickets", json=payload)
    tickets_resp = client.get("/api/ledger/tickets?date=2026-05-14&status=all")

    assert resp.status_code == 400
    assert "duplicate matchKey" in resp.json()["detail"]
    assert tickets_resp.status_code == 200
    assert tickets_resp.json() == []


def test_create_results_ticket_provider_failure_does_not_persist_pending_ticket(
    tmp_path,
    monkeypatch,
):
    client, user_store = _client(tmp_path)
    _login(client, user_store)
    ledger = importlib.import_module("app.routes.ledger")

    class FailingResultsProvider:
        def get_results_by_match_keys(self, match_keys):
            raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ledger, "get_results_provider", lambda: FailingResultsProvider())

    resp = client.post("/api/ledger/tickets", json=_payload("results"))
    tickets_resp = client.get("/api/ledger/tickets?date=2026-05-14&status=all")

    assert resp.status_code == 503
    assert "results provider failed" in resp.json()["detail"]
    assert tickets_resp.status_code == 200
    assert tickets_resp.json() == []


def test_summary_and_ticket_list_return_created_tickets(tmp_path):
    client, user_store = _client(tmp_path)
    _login(client, user_store)
    payload = _payload("schedule")
    payload["date"] = "2026-05-16"
    payload["legs"][0]["kickoffTime"] = "2026-05-16T19:00:00"
    payload["legs"][1]["kickoffTime"] = "2026-05-16T20:00:00"
    client.post("/api/ledger/tickets", json=payload)

    summary = client.get("/api/ledger/summary?start=2026-05-16&end=2026-05-16").json()
    tickets = client.get("/api/ledger/tickets?date=2026-05-16&status=all").json()

    assert summary["stake"] == 20.0
    assert summary["pendingCount"] == 1
    assert len(tickets) == 1


def test_bad_kickoff_time_ticket_does_not_break_reads(tmp_path):
    client, user_store = _client(tmp_path)
    _login(client, user_store)
    payload = _payload("schedule")
    payload["legs"][0]["kickoffTime"] = "not-a-date"

    create_resp = client.post("/api/ledger/tickets", json=payload)
    tickets_resp = client.get("/api/ledger/tickets?date=2026-05-14&status=all")
    summary_resp = client.get("/api/ledger/summary?start=2026-05-14&end=2026-05-14")

    assert create_resp.status_code == 200
    assert tickets_resp.status_code == 200
    assert summary_resp.status_code == 200
    assert tickets_resp.json()[0]["status"] == "pending"
    assert summary_resp.json()["pendingCount"] == 1


def test_reads_return_stored_data_when_best_effort_settlement_fails(tmp_path, monkeypatch):
    client, user_store = _client(tmp_path)
    _login(client, user_store)
    created = client.post("/api/ledger/tickets", json=_payload("schedule")).json()

    ledger = importlib.import_module("app.routes.ledger")

    def fail_settlement():
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(ledger, "settle_pending_tickets", fail_settlement)

    summary_resp = client.get("/api/ledger/summary?start=2026-05-14&end=2026-05-14")
    tickets_resp = client.get("/api/ledger/tickets?date=2026-05-14&status=all")
    ticket_resp = client.get(f"/api/ledger/tickets/{created['id']}")

    assert summary_resp.status_code == 200
    assert summary_resp.json()["ticketCount"] == 1
    assert tickets_resp.status_code == 200
    assert len(tickets_resp.json()) == 1
    assert ticket_resp.status_code == 200
    assert ticket_resp.json()["id"] == created["id"]


def test_ledger_requires_auth(tmp_path):
    client, _ = _client(tmp_path)
    resp = client.post("/api/ledger/tickets", json=_payload("schedule"))
    assert resp.status_code == 401
