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
    main = importlib.import_module("app.main")
    importlib.reload(main)
    from fastapi.testclient import TestClient

    return TestClient(main.app), user_mod.UserStore()


def _register_user(user_store, username: str, password: str):
    return user_store.create_user(username=username, password_hash=hash_password(password))


def test_login_success_and_me_returns_user(tmp_path):
    client, user_store = _client(tmp_path)
    _register_user(user_store, "alice", "secret123")

    login_resp = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )
    me_resp = client.get("/api/auth/me")

    assert login_resp.status_code == 200
    assert login_resp.json() == {"id": login_resp.json()["id"], "username": "alice"}
    assert me_resp.status_code == 200
    assert me_resp.json()["username"] == "alice"
    assert me_resp.json()["id"] == login_resp.json()["id"]


def test_bad_password_returns_401(tmp_path):
    client, user_store = _client(tmp_path)
    _register_user(user_store, "alice", "secret123")

    resp = client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "wrong"},
    )

    assert resp.status_code == 401
    assert resp.json()["detail"] == "用户名或密码错误"


def test_logout_clears_session(tmp_path):
    client, user_store = _client(tmp_path)
    _register_user(user_store, "alice", "secret123")
    client.post(
        "/api/auth/login",
        json={"username": "alice", "password": "secret123"},
    )

    logout_resp = client.post("/api/auth/logout")
    me_resp = client.get("/api/auth/me")

    assert logout_resp.status_code == 204
    assert me_resp.status_code == 401
