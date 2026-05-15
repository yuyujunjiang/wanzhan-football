from __future__ import annotations

from fastapi import HTTPException, Request

from app.domain.auth.models import UserOut
from app.storage.db import now_epoch
from app.storage.session_store import SessionStore
from app.storage.user_store import UserStore

SESSION_COOKIE = "fc_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60

_session_store = SessionStore()
_user_store = UserStore()


def get_current_user(request: Request) -> UserOut:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    session = _session_store.get(session_id)
    if session is None:
        raise HTTPException(status_code=401, detail="Not authenticated")

    now = now_epoch()
    if session.expires_at < now:
        _session_store.delete(session_id)
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = _user_store.get_by_id(session.user_id)
    if user is None:
        _session_store.delete(session_id)
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user
