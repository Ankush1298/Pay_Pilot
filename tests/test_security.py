"""Regression tests for the audit findings. Each fails on the pre-audit code."""

import pytest
from fastapi.testclient import TestClient

from app import agent, config, lab as LAB, merchants as M
from app.gateway import Gateway, GatewayError
from app.ledger import LedgerError
from app.main import app
from tests.test_e2e import H, register, search_and_prepare
from tests.virtual_authenticator import VirtualAuthenticator, b64u


def gw_with_trusted(uid="u_sec"):
    gw = Gateway(uid, "sec", b"k" * 32)
    dev = gw.add_device("Laptop", trusted=True)
    return gw, gw.ensure_session("ses_sec", dev["id"])


def submit(gw, sess, **kw):
    base = dict(origin="user", type="hotel", merchant_domain="grandstay.mock", pay_to=M.addr("grandstay"),
                amount=800, purpose="x", payload={})
    return gw.submit_intent(sess, **{**base, **kw})


# ---------------------------------------------------------------- auth / session
def test_logout_all_works_and_invalidates_cookie():
    c, _ = register("sec-logoutall")
    assert TestClient(app, raise_server_exceptions=False).post("/api/auth/logout-all", headers=H,
                                                              cookies=c.cookies).status_code == 200
    assert c.get("/api/auth/me").status_code == 401


def test_login_rotates_away_previous_session():
    c, a = register("sec-rotate")
    old = c.cookies.get(config.SESSION_COOKIE)
    lo = c.post("/api/auth/login/options", headers=H).json()
    assert c.post("/api/auth/login/verify", json={"credential": a.get(lo)}, headers=H).status_code == 200
    stale = TestClient(app)
    stale.cookies.set(config.SESSION_COOKIE, old)
    assert stale.get("/api/auth/me").status_code == 401


def test_cookie_flags():
    c = TestClient(app)
    a = VirtualAuthenticator(origin="https://localhost")
    h = {"Origin": "https://localhost"}
    config.ORIGINS.append("https://localhost")
    try:
        o = c.post("/api/auth/register/options", json={"username": "sec-cookie"}, headers=h).json()
        r = c.post("/api/auth/register/verify", json={"credential": a.create(o)}, headers=h)
    finally:
        config.ORIGINS.remove("https://localhost")
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc and "secure" in sc


# ---------------------------------------------------------------- webauthn
def reg_opts(c, name):
    return c.post("/api/auth/register/options", json={"username": name}, headers=H).json()


def test_registration_credential_id_must_match_authdata():
    c, a = TestClient(app), VirtualAuthenticator()
    cred = a.create(reg_opts(c, "sec-credid"), cred_id=b"\x01" * 16)     # authData says 0101.., payload id differs
    assert c.post("/api/auth/register/verify", json={"credential": cred}, headers=H).status_code == 400


@pytest.mark.parametrize("kw", [dict(flags=0x01), dict(origin="http://evil.example")])
def test_registration_requires_uv_and_origin(kw):
    c, a = TestClient(app), VirtualAuthenticator()
    cred = a.create(reg_opts(c, "sec-uv" + str(len(kw))), **kw)
    assert c.post("/api/auth/register/verify", json={"credential": cred}, headers=H).status_code == 400


def test_login_challenge_is_single_use_and_counter_must_advance():
    c, a = register("sec-counter")
    lo = c.post("/api/auth/login/options", headers=H).json()
    cred = a.get(lo, count=5)
    assert c.post("/api/auth/login/verify", json={"credential": cred}, headers=H).status_code == 200
    assert c.post("/api/auth/login/verify", json={"credential": cred}, headers=H).status_code == 400   # replay
    lo = c.post("/api/auth/login/options", headers=H).json()
    assert c.post("/api/auth/login/verify", json={"credential": a.get(lo, count=5)}, headers=H).status_code == 401


def test_assertion_for_other_users_credential_rejected():
    c1, a1 = register("sec-u1")
    c2, a2 = register("sec-u2")
    lo = c1.post("/api/auth/login/options", headers=H).json()
    cred = a2.get(lo)
    cred["response"]["userHandle"] = b64u(a1.user_handle)
    assert c1.post("/api/auth/login/verify", json={"credential": cred}, headers=H).status_code == 401


def test_approval_rejects_assertion_over_wrong_challenge():
    c, a = register("sec-wrongchal")
    search_and_prepare(c, "Find a hotel in Jaipur tomorrow", idx=-1)
    it = c.get("/api/state").json()["pending"][0]
    ao = c.post(f"/api/intents/{it['id']}/approval-options", headers=H).json()
    bad = a.get(ao, challenge="AAAA")
    assert c.post(f"/api/intents/{it['id']}/approve", json={"credential": bad}, headers=H).status_code == 403


def test_login_verify_is_rate_limited():
    c = TestClient(app)
    codes = {c.post("/api/auth/login/verify", json={"credential": {}}, headers=H).status_code for _ in range(40)}
    assert 429 in codes


# ---------------------------------------------------------------- secrets
def test_master_key_is_not_the_source_default():
    assert config.MASTER_KEY != bytes.fromhex("a1b2c3d4e5f601020304050607080900" * 2)


# ---------------------------------------------------------------- policy engine
@pytest.mark.parametrize("amt", [float("nan"), float("inf"), -5, 0])
def test_bad_amounts_never_allowed(amt):
    gw, s = gw_with_trusted()
    try:
        it = submit(gw, s, amount=amt)
    except GatewayError:
        return
    assert it["decision"]["verdict"] == "BLOCK" and it["status"] == "blocked"


def test_missing_pay_to_is_a_block_not_a_500():
    gw, s = gw_with_trusted()
    assert submit(gw, s, pay_to=None)["decision"]["verdict"] == "BLOCK"


def test_merchant_domain_case_and_whitespace_normalised():
    gw, s = gw_with_trusted()
    it = submit(gw, s, merchant_domain="  GrandStay.MOCK ")
    assert it["merchant_domain"] == "grandstay.mock" and it["decision"]["verdict"] == "ALLOW"


def test_unicode_homoglyph_domain_is_not_trusted():
    gw, s = gw_with_trusted()
    assert submit(gw, s, merchant_domain="grandstаy.mock")["decision"]["verdict"] == "BLOCK"   # Cyrillic a


def test_register_policy_cannot_mass_assign():
    c, a = TestClient(app), VirtualAuthenticator()
    cred = a.create(reg_opts(c, "sec-policy"))
    r = c.post("/api/auth/register/verify", json={"credential": cred, "policy": {"absolute_cap": 1e12}}, headers=H)
    assert r.status_code == 422


# ---------------------------------------------------------------- ledger
def test_ledger_authorization_is_single_use_and_checks_funds():
    gw, s = gw_with_trusted()
    it = submit(gw, s)
    assert it["status"] == "executed"
    from app.crypto import hmac_tag
    with pytest.raises(LedgerError):
        gw.ledger.transfer(hmac_tag(gw._exec_key, it["digest"]), it["digest"], gw.wallet, it["pay_to"], 1, "again")
    d = "f" * 64
    with pytest.raises(LedgerError):
        gw.ledger.transfer(hmac_tag(gw._exec_key, d), d, gw.wallet, it["pay_to"], 10**9, "too much")


def test_refund_does_not_reduce_balance():
    gw, s = gw_with_trusted()
    it = submit(gw, s)
    before = gw.ledger.balance_tmon()
    c_it = gw.submit_intent(s, origin="user", type="cancel_booking", payload={"booking_id": it["booking_id"]})
    assert c_it["status"] == "pending_approval"
    gw.st.intents[c_it["id"]]["status"] = "approved"
    gw._execute(gw.st.intents[c_it["id"]])
    assert gw.ledger.balance_tmon() > before


# ---------------------------------------------------------------- lab sandbox
@pytest.mark.parametrize("scenario", list(LAB.SCENARIOS))
def test_lab_never_touches_real_account(scenario):
    gw, s = gw_with_trusted("u_lab_" + scenario)
    gw.st.active_user_intent = {"kind": "movie", "city": "Goa", "budget": 100, "set_at": gw.st.now()}
    before = (len(gw.st.intents), len(gw.st.bookings), len(gw.st.executions), len(gw.st.devices),
              dict(gw.st.active_user_intent), len(gw.ledger.txs), s.get("strikes", 0))
    out = LAB.run(gw, s, gw.user_id, scenario)
    after = (len(gw.st.intents), len(gw.st.bookings), len(gw.st.executions), len(gw.st.devices),
             dict(gw.st.active_user_intent), len(gw.ledger.txs), s.get("strikes", 0))
    assert before == after and out["steps"]


def test_lab_scenarios_behave_as_described():
    gw, s = gw_with_trusted("u_lab_verdicts")
    v = lambda sc, i=0: [x for x in LAB.run(gw, s, gw.user_id, sc)["steps"]]
    assert v("auto_approve")[1]["result"]["verdict"] == "ALLOW"
    assert v("step_up")[1]["result"]["verdict"] == "STEP_UP"
    assert v("compromised_ai")[0]["result"]["decision"]["verdict"] == "BLOCK"
    assert v("lookalike")[0]["result"]["decision"]["verdict"] == "BLOCK"
    r = LAB.run(gw, s, gw.user_id, "daily_limit")["steps"]
    assert [x["result"]["decision"]["verdict"] for x in r] == ["ALLOW", "ALLOW", "STEP_UP"]
    r = LAB.run(gw, s, gw.user_id, "velocity")["steps"]
    assert [x["result"]["decision"]["verdict"] for x in r] == ["ALLOW"] * 3 + ["STEP_UP"]


# ---------------------------------------------------------------- misc input handling
def test_agent_parse_survives_garbage_budget():
    assert agent.parse("hotel under ,")["budget"] is None


def test_merchant_authorize_redirect_is_encoded():
    c = TestClient(app, follow_redirects=False)
    r = c.post("/merchant/grandstay.mock/authorize",
               data={"member": "guest", "password": "guest123", "state": "a&domain=evil.mock"}, headers=H)
    assert "evil.mock" not in r.headers["location"].split("state=")[0] and "%26" in r.headers["location"]


def test_unhandled_error_does_not_leak_details():
    c = TestClient(app, raise_server_exceptions=False)
    r = c.post("/api/auth/register/verify", json={"credential": {"response": {"clientDataJSON": 5}}}, headers=H)
    assert r.status_code < 500 and "Traceback" not in r.text


def test_session_status_is_200_for_visitors_and_users():
    c, _ = register("sec-sessionstatus")
    assert c.get("/api/auth/session").json()["authenticated"] is True
    anon = TestClient(app).get("/api/auth/session")
    assert anon.status_code == 200 and anon.json() == {"authenticated": False}


def test_global_rate_limit_returns_429_with_retry_after(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    monkeypatch.setattr(config, "RATE_LIMIT_PER_MIN", 5)
    c = TestClient(app)
    codes = [c.get("/api/auth/session").status_code for _ in range(8)]
    assert codes[:5] == [200] * 5 and set(codes[5:]) == {429}
    r = c.get("/api/auth/session")
    assert r.status_code == 429 and r.headers["retry-after"] == "60"
    assert c.get("/api/health").status_code == 200            # health checks are exempt


def test_client_ip_trusts_forwarded_for_only_from_the_local_proxy():
    from starlette.requests import Request
    from app import auth
    def req(host, xff):
        return Request({"type": "http", "client": (host, 1), "headers": [(b"x-forwarded-for", xff.encode())] if xff else []})
    assert auth.client_ip(req("127.0.0.1", "6.6.6.6, 203.0.113.9")) == "203.0.113.9"      # spoofed first entry ignored
    assert auth.client_ip(req("198.51.100.4", "6.6.6.6")) == "198.51.100.4"               # not our proxy: header ignored
    assert auth.client_ip(req("127.0.0.1", "")) == "127.0.0.1"
