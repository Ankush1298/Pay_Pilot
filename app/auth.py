"""Passkey-only account/session layer.

There are no passwords, password hashes, or recovery codes here. A discoverable
WebAuthn credential is the account authenticator. A separate httpOnly device
cookie lets PayPilot distinguish an already-trusted browser from a new one.
"""
from __future__ import annotations

import secrets
import time
from collections import defaultdict
from fastapi import HTTPException, Request, Response
from . import config

_users: dict[str, dict] = {}
_sessions: dict[str, dict] = {}
_device_tokens: dict[str, str] = {}
_usernames: dict[str, str] = {}
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
        now = time.time(); hits = [t for t in self._hits[key] if now - t < window]
        if len(hits) >= limit: self._hits[key] = hits; return False
        hits.append(now); self._hits[key] = hits; return True
LIMITER = RateLimiter()

def client_ip(request: Request) -> str:
    # Do not trust arbitrary forwarded headers in this demo.
    return request.client.host if request.client else "unknown"

class Auth:
    def __init__(self, user_id: str, username: str, session_id: str, device_id: str):
        self.user_id, self.username, self.session_id, self.device_id = user_id, username, session_id, device_id

def require(request: Request) -> Auth:
    cookie_val = request.cookies.get(SESSION_COOKIE)
    if not cookie_val: raise AuthError(401, "no_token", "Sign in with your passkey to continue")
    token = cookie_val.split(":")[0]
    if not token: raise AuthError(401, "no_token", "Sign in with your passkey to continue")
    sess = _sessions.get(token)
    if not sess or sess["exp"] < time.time() or sess["status"] != "active":
        raise AuthError(401, "session_expired", "Session expired — sign in again with your passkey")
    user = _users.get(sess["user_id"])
    if not user: raise AuthError(401, "user_gone", "Account not found")
    return Auth(sess["user_id"], user["username"], sess["id"], sess["device_id"])

def create_user(username: str, uid: str | None = None) -> str:
    name = username.strip()[:40] or f"user-{secrets.token_hex(3)}"
    key = name.lower()
    if key in _usernames: raise AuthError(409, "username_taken", "That display name is already in use")
    uid = uid or ("u_" + secrets.token_hex(16))
    _users[uid] = {"id": uid, "username": name, "created": time.time()}
    _usernames[key] = uid
    return uid

def get_user_by_id(uid: str) -> dict | None: return _users.get(uid)

def new_session(uid: str, device_id: str, ip: str, ua: str) -> tuple[str, str]:
    token = secrets.token_urlsafe(32); sid = "ses_" + secrets.token_hex(8)
    _sessions[token] = {"id": sid, "user_id": uid, "device_id": device_id, "status": "active",
                        "exp": time.time() + config.SESSION_TTL, "ip": ip, "ua": ua[:200], "created": time.time()}
    return token, sid

def revoke_session(session_id: str):
    for s in _sessions.values():
        if s["id"] == session_id: s["status"] = "revoked"

def revoke_user_sessions(uid: str):
    for s in _sessions.values():
        if s["user_id"] == uid: s["status"] = "revoked"

def list_sessions(uid: str) -> list[dict]:
    now = time.time()
    return [{"id": s["id"], "device_id": s["device_id"], "ip": s["ip"], "ua": s["ua"], "created": s["created"], "exp": s["exp"]}
            for s in _sessions.values() if s["user_id"] == uid and s["status"] == "active" and s["exp"] > now]

def bind_device(uid: str, device_id: str) -> str:
    token = secrets.token_urlsafe(32); _device_tokens[token] = f"{uid}:{device_id}"; return token

def device_for_token(token: str | None, uid: str) -> str | None:
    if not token: return None
    v = _device_tokens.get(token)
    if not v: return None
    bound_uid, did = v.split(":", 1)
    return did if bound_uid == uid else None

def set_cookies(response: Response, session_token: str, device_token: str | None = None):
    kw = dict(httponly=True, samesite="lax", path="/")
    val = f"{session_token}:{device_token or ''}"
    response.set_cookie(SESSION_COOKIE, val, max_age=365 * 86400, **kw)

def clear_session_cookie(request: Request, response: Response):
    cookie_val = request.cookies.get(SESSION_COOKIE) or ""
    dtoken = cookie_val.split(":")[1] if ":" in cookie_val else None
    if dtoken:
        kw = dict(httponly=True, samesite="lax", path="/")
        response.set_cookie(SESSION_COOKIE, f":{dtoken}", max_age=365 * 86400, **kw)
    else:
        response.delete_cookie(SESSION_COOKIE)
