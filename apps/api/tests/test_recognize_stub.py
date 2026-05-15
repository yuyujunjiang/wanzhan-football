import importlib
import os

from fastapi.testclient import TestClient


def test_recognize_ticket_stub_returns_draft() -> None:
    os.environ["FC_SQLITE_PATH"] = ":memory:"
    app_settings = importlib.import_module("app.settings")
    importlib.reload(app_settings)
    app_main = importlib.import_module("app.main")
    importlib.reload(app_main)

    client = TestClient(app_main.app)

    resp = client.post(
        "/api/tickets/recognize",
        files=[("images", ("ticket.jpg", b"fake", "image/jpeg"))],
    )

    assert resp.status_code == 200
    body = resp.json()
    assert "id" in body
    assert body["id"]
    assert {k: v for k, v in body.items() if k != "id"} == {
        "ticketType": "jc-football",
        "playType": "SPF",
        "multiplier": 2,
        "passTypes": ["2x1"],
        "legs": [
            {
                "matchKey": "2026-05-08 EPL A vs B",
                "playType": "SPF",
                "selection": "胜",
                "handicap": None,
                "sp": 1.85,
            },
            {
                "matchKey": "2026-05-08 EPL C vs D",
                "playType": "SPF",
                "selection": "平",
                "handicap": None,
                "sp": 2.1,
            },
        ],
        "warnings": [],
        "sourceImages": ["ticket.jpg"],
    }

