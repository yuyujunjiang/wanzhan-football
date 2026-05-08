from fastapi.testclient import TestClient

from app.main import app


def test_recognize_ticket_stub_returns_draft() -> None:
    client = TestClient(app)

    resp = client.post(
        "/api/tickets/recognize",
        files=[("images", ("ticket.jpg", b"fake", "image/jpeg"))],
    )

    assert resp.status_code == 200
    assert resp.json() == {
        "ticketType": "jc-football",
        "playType": "SPF",
        "multiplier": 2,
        "passTypes": ["2x1"],
        "legs": [
            {"matchKey": "2026-05-08 EPL A vs B", "selection": "胜", "handicap": None, "sp": 1.85},
            {"matchKey": "2026-05-08 EPL C vs D", "selection": "平", "handicap": None, "sp": 2.1},
        ],
        "warnings": [],
        "sourceImages": ["ticket.jpg"],
    }

