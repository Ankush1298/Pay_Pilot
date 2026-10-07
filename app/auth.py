"""Passkey-only account/session layer.

There are no passwords, password hashes, or recovery codes here. A discoverable
WebAuthn credential is the account authenticator. A separate httpOnly device
cookie lets PayPilot distinguish an already-trusted browser from a new one.
"""
from __future__ import annotations

import hashlib
import secrets
import time
from collections import defaultdict
from fastapi import HTTPException, Request, Response
from sqlalchemy import delete, insert, select, update
from sqlalchemy.exc import IntegrityError
from . import config
from .db import device_tokens, engine, sessions, users

def _h(token: str) -> str:
    """Tokens are stored only as hashes: a database leak cannot be replayed as a cookie."""
    return hashlib.sha256(token.encode()).hexdigest()

SESSION_COOKIE = config.SESSION_COOKIE
DEVICE_COOKIE = config.DEVICE_COOKIE

class AuthState:
    def __init__(self):
        self.challenges: dict[str, dict] = {}
AUTH_STATE = AuthState()

class AuthError(HTTPException):
    def __init__(self, status: int, code: str, message: str, headers: dict | None = None):
        super().__init__(status_code=status, detail={"code": code, "message": message}, headers=headers or {})

class RateLimiter:
    def __init__(self): self._hits = defaultdict(list)
    def allow(self, key: str, limit: int, window: int) -> bool:
        now = time.time()
        if len(self._hits) > 20000:                    # drop idle keys so scanners cannot grow memory without bound
            self._hits = defaultdict(list, {k: v for k, v in self._hits.items() if v and now - v[-1] < 3600})
        hits = [t for t in self._hits[key] if now - t < window]
        if len(hits) >= limit: self._hits[key] = hits; return False
        hits.append(now); self._hits[key] = hits; return True
LIMITER = RateLimiter()

def client_ip(request: Request) -> str:
    host = request.client.host if request.client else "unknown"
    if host in ("127.0.0.1", "::1"):
        # Our own frontend proxy: trust the address it appended (the LAST entry; earlier ones are client-supplied).
        fwd = request.headers.get("x-forwarded-for", "").split(",")[-1].strip()
        if fwd: return fwd[:64]
    return host

class Auth:
    def __init__(self, user_id: str, username: str, session_id: str, device_id: str):
        self.user_id, self.username, self.session_id, self.device_id = user_id, username, session_id, device_id

def require(request: Request) -> Auth:
    cookie_val = request.cookies.get(SESSION_COOKIE)
    if not cookie_val: raise AuthError(401, "no_token", "Sign in with your passkey to continue")
    token = cookie_val.split(":")[0]
    if not token: raise AuthError(401, "no_token", "Sign in with your passkey to continue")
    with engine.connect() as c:
        sess = c.execute(select(sessions).where(sessions.c.token_hash == _h(token))).mappings().first()
        if not sess or sess["exp"] < time.time() or sess["status"] != "active":
            raise AuthError(401, "session_expired", "Session expired — sign in again with your passkey")
        user = c.execute(select(users).where(users.c.id == sess["user_id"])).mappings().first()
    if not user: raise AuthError(401, "user_gone", "Account not found")
    return Auth(sess["user_id"], user["username"], sess["id"], sess["device_id"])

def create_user(username: str, uid: str | None = None) -> str:
    name = username.strip()[:40] or f"user-{secrets.token_hex(3)}"
    uid = uid or ("u_" + secrets.token_hex(16))
    try:
        with engine.begin() as c:
            c.execute(insert(users).values(id=uid, username=name, username_key=name.lower(), created=time.time()))
    except IntegrityError:      # the unique constraint is the race-proof check
        raise AuthError(409, "username_taken", "That display name is already in use")
    return uid

def delete_user(uid: str) -> None:
    with engine.begin() as c:
        c.execute(delete(users).where(users.c.id == uid))     # sessions, device tokens and snapshot cascade

def get_user_by_id(uid: str) -> dict | None:
    with engine.connect() as c:
        row = c.execute(select(users).where(users.c.id == uid)).mappings().first()
    return {"id": row["id"], "username": row["username"], "created": row["created"]} if row else None

def new_session(uid: str, device_id: str, ip: str, ua: str) -> tuple[str, str]:
    purge_expired()
    token = secrets.token_urlsafe(32); sid = "ses_" + secrets.token_hex(8)
    with engine.begin() as c:
        c.execute(insert(sessions).values(token_hash=_h(token), id=sid, user_id=uid, device_id=device_id, status="active",
                                          exp=time.time() + config.SESSION_TTL, ip=(ip or "")[:64], ua=(ua or "")[:200], created=time.time()))
    return token, sid

def revoke_session(session_id: str):
    with engine.begin() as c:
        c.execute(update(sessions).where(sessions.c.id == session_id).values(status="revoked"))

def revoke_user_sessions(uid: str):
    with engine.begin() as c:
        c.execute(update(sessions).where(sessions.c.user_id == uid).values(status="revoked"))

def list_sessions(uid: str) -> list[dict]:
    with engine.connect() as c:
        rows = c.execute(select(sessions).where(sessions.c.user_id == uid, sessions.c.status == "active",
                                                 sessions.c.exp > time.time())).mappings().all()
    return [{"id": r["id"], "device_id": r["device_id"], "ip": r["ip"], "ua": r["ua"], "created": r["created"], "exp": r["exp"]} for r in rows]

def bind_device(uid: str, device_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with engine.begin() as c:
        c.execute(insert(device_tokens).values(token_hash=_h(token), user_id=uid, device_id=device_id))
    return token

def device_for_token(token: str | None, uid: str) -> str | None:
    if not token: return None
    with engine.connect() as c:
        row = c.execute(select(device_tokens).where(device_tokens.c.token_hash == _h(token))).mappings().first()
    return row["device_id"] if row and row["user_id"] == uid else None

def _is_https(request: Request) -> bool:
    return (request.headers.get("origin") or "").startswith("https://") or request.url.scheme == "https"

def set_cookies(request: Request, response: Response, session_token: str, device_token: str | None = None):
    response.set_cookie(SESSION_COOKIE, f"{session_token}:{device_token or ''}", max_age=config.COOKIE_MAX_AGE,
                        httponly=True, samesite="lax", path="/", secure=_is_https(request))

def device_token_of(request: Request) -> str | None:
    cookie_val = request.cookies.get(SESSION_COOKIE) or ""
    return cookie_val.split(":", 1)[1] or None if ":" in cookie_val else None

def clear_session_cookie(request: Request, response: Response):
    """Drop the session token but keep the device token, so this browser is still recognised at next login."""
    dtoken = device_token_of(request)
    if dtoken:
        response.set_cookie(SESSION_COOKIE, f":{dtoken}", max_age=config.COOKIE_MAX_AGE, httponly=True,
                            samesite="lax", path="/", secure=_is_https(request))
    else:
        response.delete_cookie(SESSION_COOKIE, path="/")

def revoke_cookie_session(request: Request):
    """Rotation: signing in again ends the session this browser was holding."""
    tok = (request.cookies.get(SESSION_COOKIE) or "").split(":")[0]
    if tok:
        with engine.begin() as c:
            c.execute(update(sessions).where(sessions.c.token_hash == _h(tok)).values(status="revoked"))

_last_purge = 0.0

def purge_expired():
    global _last_purge
    now = time.time()
    if now - _last_purge > 60:          # at most once a minute: a range DELETE on every login would contend under load
        _last_purge = now
        with engine.begin() as c:
            c.execute(delete(sessions).where((sessions.c.exp < now) | (sessions.c.status != "active")))
    for k in [k for k, ch in AUTH_STATE.challenges.items() if ch["exp"] < now]:
        AUTH_STATE.challenges.pop(k, None)
