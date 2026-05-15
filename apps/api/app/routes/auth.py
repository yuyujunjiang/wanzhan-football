from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse, Response

from app.auth.deps import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    get_current_user,
)
from app.domain.auth.models import LoginRequest, UserOut
from app.domain.auth.passwords import verify_password
from app.settings import settings
from app.storage.db import now_epoch
from app.storage.session_store import SessionStore
from app.storage.user_store import UserStore

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _cookie_secure(request: Request) -> bool:
    if settings.cookie_secure:
        return True
    forwarded = request.headers.get("x-forwarded-proto", "").split(",")[0].strip().lower()
    return forwarded == "https"

_session_store = SessionStore()
_user_store = UserStore()


@router.post("/login")
def login(body: LoginRequest, request: Request) -> UserOut:
    user = _user_store.get_by_username(body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    session_id = secrets.token_urlsafe(32)
    expires_at = now_epoch() + SESSION_MAX_AGE
    _session_store.create(session_id, user.id, expires_at)

    response = JSONResponse(content=UserOut(id=user.id, username=user.username).model_dump())
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        httponly=True,
        max_age=SESSION_MAX_AGE,
        samesite="lax",
        path="/",
        secure=_cookie_secure(request),
    )
    return response


@router.post("/logout")
def logout(request: Request) -> Response:
    session_id = request.cookies.get(SESSION_COOKIE)
    if session_id:
        _session_store.delete(session_id)

    response = Response(status_code=204)
    response.delete_cookie(SESSION_COOKIE, path="/", secure=_cookie_secure(request))
    return response


@router.get("/me")
def me(user: UserOut = Depends(get_current_user)) -> UserOut:
    return user
