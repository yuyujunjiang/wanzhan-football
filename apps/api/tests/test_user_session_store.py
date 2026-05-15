import importlib
import os

from app.domain.auth.passwords import hash_password


def _stores(tmp_path):
    os.environ["FC_SQLITE_PATH"] = str(tmp_path / "auth.sqlite3")
    settings = importlib.import_module("app.settings")
    importlib.reload(settings)
    user_mod = importlib.import_module("app.storage.user_store")
    session_mod = importlib.import_module("app.storage.session_store")
    importlib.reload(user_mod)
    importlib.reload(session_mod)
    return user_mod.UserStore(), session_mod.SessionStore()


def test_create_user_normalizes_username(tmp_path):
    user_store, _ = _stores(tmp_path)

    user = user_store.create_user(username="  Alice  ", password_hash=hash_password("pw"))

    assert user.username == "alice"
    loaded = user_store.get_by_username("ALICE")
    assert loaded is not None
    assert loaded.id == user.id
    assert loaded.password_hash != "pw"


def test_get_by_id_returns_user_out(tmp_path):
    user_store, _ = _stores(tmp_path)

    created = user_store.create_user(username="bob", password_hash=hash_password("secret"))
    loaded = user_store.get_by_id(created.id)

    assert loaded == created
    assert user_store.get_by_id("missing") is None


def test_create_get_and_delete_session(tmp_path):
    user_store, session_store = _stores(tmp_path)
    user = user_store.create_user(username="carol", password_hash=hash_password("pw"))
    session_id = "sess-abc123"
    expires_at = 9_999_999_999

    created = session_store.create(session_id, user.id, expires_at)
    assert created.id == session_id
    assert created.user_id == user.id
    assert created.expires_at == expires_at

    loaded = session_store.get(session_id)
    assert loaded is not None
    assert loaded.user_id == user.id

    session_store.delete(session_id)
    assert session_store.get(session_id) is None


def test_delete_expired_removes_only_stale_sessions(tmp_path):
    _, session_store = _stores(tmp_path)
    session_store.create("old", "user-1", expires_at=100)
    session_store.create("fresh", "user-1", expires_at=9_999_999_999)

    removed = session_store.delete_expired(now=200)

    assert removed == 1
    assert session_store.get("old") is None
    assert session_store.get("fresh") is not None
