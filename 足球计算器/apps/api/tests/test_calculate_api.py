import importlib
import os


def test_calculate_ticket_persists_report(tmp_path) -> None:
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "test.sqlite3")

    # Import after env var so app uses test DB.
    app_settings = importlib.import_module("app.settings")
    importlib.reload(app_settings)
    app_main = importlib.import_module("app.main")
    importlib.reload(app_main)

    from fastapi.testclient import TestClient

    client = TestClient(app_main.app)

    payload = {
        "ticketType": "jc-football",
        "playType": "SPF",
        "multiplier": 2,
        "passTypes": ["2x1"],
        "legs": [
            {"matchKey": "2026-05-08 EPL A vs B", "selection": "胜", "handicap": None, "sp": 1.85},
            {"matchKey": "2026-05-08 EPL C vs D", "selection": "平", "handicap": None, "sp": 2.1},
        ],
    }

    resp = client.post("/api/tickets/calculate", json=payload)

    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["report"]["totalPayout"] == 15.54

    ticket_id = body["id"]
    fetch = client.get(f"/api/tickets/{ticket_id}")
    assert fetch.status_code == 200
    stored = fetch.json()
    assert stored["id"] == ticket_id
    assert stored["ticket"]["multiplier"] == 2
    assert stored["report"]["totalPayout"] == 15.54

