"""PayPilot API. Run:  uvicorn app.main:app --port 8000   (the Next.js app proxies /api to it)"""
from __future__ import annotations

import time
from fastapi import Depends, FastAPI, Form, HTTPException, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from . import auth, config, lab as LAB
from . import merchants as M
from . import passkeys as PK
from .agent import AGENT
from .auth import Auth
from .gateway import GatewayError
from .ledger import Ledger
from .registry import REG
from .state import State

app = FastAPI(title="PayPilot API", version="2.0.0", docs_url=None, redoc_url=None)


# --------------------------------------------------------------- middleware
@app.middleware("http")
async def security(request: Request, call_next):
    if request.method in {"POST", "PUT", "PATCH", "DELETE"} and request.url.path.startswith("/api/"):
        origin = request.headers.get("origin")
        if origin and origin.rstrip("/") not in config.ORIGINS:        # CSRF defence (plus SameSite=Lax cookies)
            return JSONResponse({"detail": {"code": "bad_origin", "message": "Cross-site request refused"}}, 403)
        if request.headers.get("sec-fetch-site") == "cross-site":
            return JSONResponse({"detail": {"code": "cross_site", "message": "Cross-site request refused"}}, 403)
    resp = await call_next(request)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    if request.url.path.startswith("/api/"):
        resp.headers["Cache-Control"] = "no-store"
    return resp


def origin_of(request: Request) -> str:
    return request.headers.get("origin") or config.ORIGINS[0]


def run(a: Auth, fn, *args, **kw):
    """Run fn(gateway, session, ...) under the per-user lock; always persist; map errors to HTTP."""
    with REG.use(a.user_id) as gw:
        sess = gw.ensure_session(a.session_id, a.device_id)
        try:
            return fn(gw, sess, *args, **kw)
        except GatewayError as e:
            raise HTTPException(e.status, {"code": e.code, "message": e.message})


def ua_label(ua: str) -> str:
    u = ua or ""
    br = next((n for k, n in (("Edg/", "Edge"), ("OPR/", "Opera"), ("Firefox/", "Firefox"), ("Chrome/", "Chrome"),
                              ("Safari/", "Safari")) if k in u), "Browser")
    os_ = next((n for k, n in (("Windows", "Windows"), ("Android", "Android"), ("iPhone", "iPhone"), ("iPad", "iPad"),
                               ("Mac OS", "macOS"), ("Linux", "Linux")) if k in u), "unknown OS")
    return f"{br} on {os_}"


# ------------------------------------------------------------------- models
class RegisterOptionsReq(BaseModel):
    username: str = Field(max_length=40)

class LoginVerifyReq(BaseModel):
    credential: dict
    device_name: str | None = Field(default=None, max_length=40)

class RegisterVerifyReq(BaseModel):
    credential: dict
    device_name: str | None = Field(default=None, max_length=40)
    policy: dict | None = None


class ChatReq(BaseModel):
    message: str = Field(min_length=1, max_length=600)


class PrepareReq(BaseModel):
    option_id: str


class CredReq(BaseModel):
    credential: dict


class PasskeyReq(BaseModel):
    credential: dict
    name: str = Field(default="", max_length=40)


class PolicyReq(BaseModel):
    policy: dict


class ManageReq(BaseModel):
    units: int | None = None


class LabReq(BaseModel):
    scenario: str


# --------------------------------------------------------------------- passkey-only auth
@app.post("/api/auth/register/options")
def register_options(req: RegisterOptionsReq, request: Request):
    ip = auth.client_ip(request)
    if not auth.LIMITER.allow(f"reg:{ip}", 10, 3600):
        raise auth.AuthError(429, "rate_limited", "Too many sign-ups from this network. Try later.")
    name = (req.username or "").strip()[:40] or f"User {__import__('secrets').token_hex(3)}"
    user_id = "u_" + __import__("secrets").token_hex(16)
    opts = PK.registration_options(auth.AUTH_STATE, user_id, name, origin_of(request))
    challenge = opts["challenge"]
    auth.AUTH_STATE.challenges[challenge]["username"] = name
    auth.AUTH_STATE.challenges[challenge]["user_id"] = user_id
    return opts

@app.post("/api/auth/register/verify")
def register_verify(req: RegisterVerifyReq, request: Request, response: Response):
    origin = origin_of(request); ip, ua = auth.client_ip(request), request.headers.get("user-agent", "")
    cd = req.credential.get("response", {})
    try:
        _, challenge = PK._parse_client_data(cd.get("clientDataJSON", ""), "webauthn.create", PK.resolve_origin(origin))
    except PK.PasskeyError as e:
        raise auth.AuthError(400, e.code, e.message)
    c = auth.AUTH_STATE.challenges.pop(challenge, None)
    if not c or c.get("purpose") != "register" or c["exp"] < time.time():
        raise auth.AuthError(400, "bad_challenge", "Challenge expired or invalid")
    st = State(); st.challenges[challenge] = c
    try:
        cred = PK.verify_registration(st, "temp", origin, req.credential, req.device_name or "Passkey")
    except PK.PasskeyError as e:
        raise auth.AuthError(400, e.code, e.message)
    user_id = c["user_id"]; username = c["username"]
    auth.create_user(username, uid=user_id)
    with REG.use(user_id) as gw:
        dev = gw.add_device(req.device_name or ua_label(ua), ua, ip, trusted=True)
        cred["device_id"] = dev["id"]
        gw.st.credentials[cred["id"]] = cred
        if req.policy:
            gw._apply_policy(req.policy)
        # In live mode this also deploys the deterministic smart account owned by this P-256 key.
        try:
            gw.initialize_wallet(cred)
        except Exception as e:
            # Do not leave an account claiming to be on-chain when deployment is unavailable.
            auth._users.pop(user_id, None); auth._usernames.pop(username.lower(), None)
            raise auth.AuthError(503, "wallet_setup_failed", f"Smart-account setup failed: {e}")
        dtoken = auth.bind_device(user_id, dev["id"]); token, sid = auth.new_session(user_id, dev["id"], ip, ua)
        gw.ensure_session(sid, dev["id"]); gw.st.onboarding_open = False; gw.st.log("account", "Account created with a discoverable passkey", "ok")
    auth.set_cookies(response, token, dtoken)
    return {"user": {"id": user_id, "username": username}, "device": dev, "wallet_address": gw.wallet}

@app.post("/api/auth/login/options")
def login_options(request: Request):
    ip = auth.client_ip(request)
    if not auth.LIMITER.allow(f"login:{ip}", 30, 300):
        raise auth.AuthError(429, "rate_limited", "Too many attempts from this network.", headers={"Retry-After": "300"})
    challenge = PK.new_challenge(auth.AUTH_STATE, "login")
    return {"challenge": challenge, "rpId": PK._rp_id(origin_of(request)), "userVerification": "required", "timeout": 120_000}

@app.post("/api/auth/login/verify")
def login_verify(req: LoginVerifyReq, request: Request, response: Response):
    origin = origin_of(request); ip, ua = auth.client_ip(request), request.headers.get("user-agent", "")
    cd = req.credential.get("response", {})
    try:
        _, challenge = PK._parse_client_data(cd.get("clientDataJSON", ""), "webauthn.get", PK.resolve_origin(origin))
    except PK.PasskeyError as e:
        raise auth.AuthError(400, e.code, e.message)
    c = auth.AUTH_STATE.challenges.pop(challenge, None)
    if not c or c.get("purpose") != "login" or c["exp"] < time.time():
        raise auth.AuthError(400, "bad_challenge", "Challenge expired or invalid")
    user_handle = cd.get("userHandle")
    if not user_handle:
        raise auth.AuthError(400, "no_user_handle", "This account requires a discoverable passkey")
    try: user_id = PK._b64u_decode(user_handle).decode()
    except Exception: raise auth.AuthError(400, "bad_user_handle", "Invalid passkey user handle")
    user = auth.get_user_by_id(user_id)
    if not user: raise auth.AuthError(401, "unknown_user", "Account not found")
    with REG.use(user_id) as gw:
        try: PK.verify_assertion(gw.st, origin, req.credential, challenge, list(gw.st.credentials.keys()))
        except PK.PasskeyError as e: raise auth.AuthError(401, e.code, e.message)
        cookie_val = request.cookies.get(auth.SESSION_COOKIE) or ""
        dtoken = cookie_val.split(":")[1] if ":" in cookie_val else None
        cookie_device = auth.device_for_token(dtoken, user_id)
        dev = gw.st.devices.get(cookie_device) if cookie_device else None
        if dev and dev["status"] == "blocked":
            raise auth.AuthError(403, "device_blocked", "This device is blocked")
        if not dev:
            dev = gw.add_device(req.device_name or ua_label(ua), ua, ip, trusted=False)
        dtoken = auth.bind_device(user_id, dev["id"])
        token, sid = auth.new_session(user_id, dev["id"], ip, ua)
        gw.ensure_session(sid, dev["id"])
        gw.st.log("session", f"Signed in with discoverable passkey from {ip}", "info")
    auth.set_cookies(response, token, dtoken)
    return {"user": {"id": user_id, "username": user["username"]}, "device": dev, "new_device": dev["status"] != "trusted"}

@app.post("/api/auth/logout")
def logout(request: Request, response: Response, a: Auth = Depends(auth.require)):
    auth.revoke_session(a.session_id)
    auth.clear_session_cookie(request, response)
    return {"ok": True}


@app.post("/api/auth/logout-all")
def logout_all(response: Response, a: Auth = Depends(auth.require)):
    auth.revoke_user_sessions(a.user_id)
    auth.clear_session_cookie(response)
    return {"ok": True}


@app.get("/api/auth/me")
def me(a: Auth = Depends(auth.require)):
    with REG.use(a.user_id) as gw:
        return {"id": a.user_id, "username": a.username, "device_id": a.device_id, "wallet_address": gw.wallet, "has_passkey": bool(gw.st.credentials), "ledger_network": gw.ledger.network}


@app.get("/api/auth/sessions")
def sessions(a: Auth = Depends(auth.require)):
    with REG.use(a.user_id) as gw:
        devs = gw.st.devices
        return [{**s, "device_name": devs.get(s["device_id"], {}).get("name", "?"), "current": s["id"] == a.session_id}
                for s in auth.list_sessions(a.user_id)]


@app.delete("/api/auth/sessions/{session_id}")
def end_session(session_id: str, a: Auth = Depends(auth.require)):
    mine = {s["id"] for s in auth.list_sessions(a.user_id)}
    if session_id not in mine:
        raise HTTPException(404, {"code": "no_session", "message": "Unknown session"})
    auth.revoke_session(session_id)
    return {"ok": True}

# ---------------------------------------------------------------- app state
@app.get("/api/state")
def state(a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.public_state(s))


@app.post("/api/onboarding/policy")
def onboarding_policy(req: PolicyReq, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.initial_policy(s, req.policy))


@app.post("/api/onboarding/complete")
def onboarding_complete(a: Auth = Depends(auth.require)):
    run(a, lambda gw, s: gw.finish_onboarding(s))
    return {"ok": True}


@app.post("/api/policy/propose")
def propose_policy(req: PolicyReq, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.propose_policy(s, req.policy))



# ----------------------------------------------------------------- passkeys
@app.post("/api/passkeys/register/options")
def pk_options(request: Request, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.passkey_register_options(s, origin_of(request), a.username))


@app.post("/api/passkeys/register/verify")
def pk_verify(req: PasskeyReq, request: Request, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.passkey_register_verify(s, origin_of(request), req.credential, req.name))


# --------------------------------------------------------------- devices
@app.post("/api/devices/{device_id}/approve")
def approve_device(device_id: str, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.request_device_approval(s, device_id))


@app.post("/api/devices/{device_id}/block")
def block_device(device_id: str, a: Auth = Depends(auth.require)):
    run(a, lambda gw, s: gw.block_device(s, device_id))
    return {"ok": True}


# -------------------------------------------------------------------- agent
@app.post("/api/agent/chat")
def agent_chat(req: ChatReq, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: AGENT.chat(gw, a.user_id, req.message))


@app.post("/api/agent/prepare")
def agent_prepare(req: PrepareReq, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: AGENT.prepare(gw, s, a.user_id, req.option_id))


@app.post("/api/agent/bookings/{booking_id}/{action}")
def agent_manage(booking_id: str, action: str, req: ManageReq, a: Auth = Depends(auth.require)):
    if action not in {"cancel", "modify"}:
        raise HTTPException(404, "unknown action")
    return run(a, lambda gw, s: AGENT.manage_booking(gw, s, action, booking_id, req.units))


# ---------------------------------------------------------------- approvals
@app.post("/api/intents/{intent_id}/approval-options")
def approval_options(intent_id: str, request: Request, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.approval_options(s, intent_id, origin_of(request)))


@app.post("/api/intents/{intent_id}/approve")
def approve(intent_id: str, req: CredReq, request: Request, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.approve(s, intent_id, origin_of(request), req.credential))


@app.post("/api/intents/{intent_id}/reject")
def reject(intent_id: str, a: Auth = Depends(auth.require)):
    return run(a, lambda gw, s: gw.reject(s, intent_id))



# -------------------------------------------------------------- connections
@app.post("/api/connections/{domain}/start")
def connect_start(domain: str, a: Auth = Depends(auth.require)):
    return {"url": run(a, lambda gw, s: gw.connect_start(s, domain))}


@app.get("/api/connections/callback")
def connect_callback(domain: str, state: str, code: str, a: Auth = Depends(auth.require)):
    try:
        run(a, lambda gw, s: gw.connect_finish(s, domain, state, code))
    except HTTPException:
        return RedirectResponse("/settings?error=1", 303)
    return RedirectResponse(f"/settings?connected={domain}", 303)


@app.delete("/api/connections/{domain}")
def disconnect(domain: str, a: Auth = Depends(auth.require)):
    run(a, lambda gw, s: gw.disconnect(s, domain))
    return {"ok": True}


# ---------------------------------------------------------------------- lab
@app.get("/api/lab/scenarios")
def lab_list(a: Auth = Depends(auth.require)):
    return [{"id": k, "title": v[0], "story": v[1]} for k, v in LAB.SCENARIOS.items()]


@app.post("/api/lab/run")
def lab_run(req: LabReq, a: Auth = Depends(auth.require)):
    if not auth.LIMITER.allow(f"lab:{a.user_id}", 40, 600):
        raise HTTPException(429, {"code": "rate_limited", "message": "Slow down"})
    return run(a, lambda gw, s: LAB.run(gw, s, a.user_id, req.scenario))


# ----------------------------------------------------- mock merchant websites
@app.get("/merchant/{domain}", response_class=HTMLResponse)
def merchant_page(domain: str):
    return M.render_page(domain)


@app.get("/merchants", response_class=HTMLResponse)
def merchants_index():
    links = "".join(f"<li><a href='/merchant/{d}'>{d}</a> ({'verified' if m['verified'] else 'UNVERIFIED'})</li>"
                    for d, m in M.REGISTRY.items())
    return f"<h1>Mock merchants</h1><ul>{links}</ul>"


@app.get("/merchant/{domain}/authorize", response_class=HTMLResponse)
def merchant_authorize(domain: str, state: str = ""):
    return M.authorize_page(domain, state)


@app.post("/merchant/{domain}/authorize")
def merchant_authorize_post(domain: str, member: str = Form(""), password: str = Form(""), state: str = Form("")):
    code = M.issue_code(domain, member, password, state)     # the password never leaves this function
    if not code:
        return HTMLResponse(M.authorize_page(domain, state).replace("<h1>", "<p style='color:#b4231b'>Check your credentials.</p><h1>", 1), 401)
    return RedirectResponse(f"/api/connections/callback?domain={domain}&state={state}&code={code}", 303)


@app.get("/api/health")
def health():
    return {"ok": True, "ledger": Ledger.network}


print(f"[PayPilot] ledger mode: {Ledger.network}  (expected 'simulated' for the demo)")
