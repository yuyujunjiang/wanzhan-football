import importlib
import os


def _make_client(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "test.sqlite3")
    os.environ["FC_RESULTS_PROVIDER"] = "mock"
    os.environ["FC_MATCHES_SCHEDULER_ENABLED"] = "false"

    # Import after env var so app uses test DB.
    app_settings = importlib.import_module("app.settings")
    importlib.reload(app_settings)
    app_main = importlib.import_module("app.main")
    importlib.reload(app_main)

    from fastapi.testclient import TestClient

    return TestClient(app_main.app)


def test_matches_requires_date(tmp_path) -> None:
    client = _make_client(tmp_path)

    resp = client.get("/api/matches")
    assert resp.status_code == 422


def test_matches_returns_deterministic_list(tmp_path) -> None:
    client = _make_client(tmp_path)

    resp = client.get("/api/matches?date=2026-05-08")
    assert resp.status_code == 200

    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 1
    assert all(m["date"] == "2026-05-08" for m in body)


def test_matches_rejects_bad_date_format(tmp_path) -> None:
    client = _make_client(tmp_path)

    resp = client.get("/api/matches?date=20260508")
    assert resp.status_code == 422


def test_matches_range_returns_day_groups(tmp_path) -> None:
    client = _make_client(tmp_path)

    resp = client.get("/api/matches/range?start=2026-05-08&days=3")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 3
    assert body[0]["date"] == "2026-05-08"
    assert "matches" in body[0]
