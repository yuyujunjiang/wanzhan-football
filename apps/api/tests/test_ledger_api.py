import importlib
import os


def _client(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "api.sqlite3")
    os.environ["FC_RESULTS_PROVIDER"] = "mock"
    os.environ["FC_MATCHES_SCHEDULER_ENABLED"] = "false"
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    main = importlib.import_module("app.main")
    importlib.reload(main)
    from fastapi.testclient import TestClient

    return TestClient(main.app)


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
    client = _client(tmp_path)

    resp = client.post("/api/ledger/tickets", json=_payload("schedule"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "pending"
    assert body["passType"] == "2x1"
    assert body["stake"] == 20.0
    assert body["estimatedPayout"] == 60.0


def test_create_results_ticket_settles_immediately_with_mock_results(tmp_path):
    client = _client(tmp_path)

    resp = client.post("/api/ledger/tickets", json=_payload("results"))

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "settled"
    assert body["actualPayout"] == 60.0
    assert body["profit"] == 40.0


def test_summary_and_ticket_list_return_created_tickets(tmp_path):
    client = _client(tmp_path)
    client.post("/api/ledger/tickets", json=_payload("schedule"))

    summary = client.get("/api/ledger/summary?start=2026-05-14&end=2026-05-14").json()
    tickets = client.get("/api/ledger/tickets?date=2026-05-14&status=all").json()

    assert summary["stake"] == 20.0
    assert summary["pendingCount"] == 1
    assert len(tickets) == 1
