"""Full lifecycle through the HTTP API with a virtual passkey: register -> login -> intent -> step-up -> execute."""
from fastapi.testclient import TestClient

from app.main import app
from tests.virtual_authenticator import ORIGIN, VirtualAuthenticator

H = {"Origin": ORIGIN}


def register(name="e2e-user"):
    c, a = TestClient(app), VirtualAuthenticator()
    opts = c.post("/api/auth/register/options", json={"username": name}, headers=H).json()
    r = c.post("/api/auth/register/verify", json={"credential": a.create(opts)}, headers=H)
    assert r.status_code == 200, r.text
    return c, a


def search_and_prepare(c, msg, idx=0):
    opts = c.post("/api/agent/chat", json={"message": msg}, headers=H).json()["options"]
    return c.post("/api/agent/prepare", json={"option_id": opts[idx]["id"]}, headers=H).json()


def test_register_login_autoapprove_and_ledger():
    c, a = register("e2e-auto")
    assert c.get("/api/auth/me").status_code == 200
    c.post("/api/auth/logout", headers=H)
    assert c.get("/api/auth/me").status_code == 401
    lo = c.post("/api/auth/login/options", headers=H).json()
    r = c.post("/api/auth/login/verify", json={"credential": a.get(lo)}, headers=H)
    assert r.status_code == 200 and r.json()["new_device"] is False
    it = search_and_prepare(c, "Find a hotel in Jaipur under 1000 tomorrow")
    assert it["status"] == "executed" and it["booking_id"] and it["tx_hash"]
    st = c.get("/api/state").json()
    assert st["bookings"][0]["id"] == it["booking_id"] and st["ledger"]["txs"][0]["tx_hash"] == it["tx_hash"]


def test_step_up_with_passkey_assertion_then_execute():
    c, a = register("e2e-stepup")
    it = search_and_prepare(c, "Find a hotel in Jaipur tomorrow", idx=-1)
    pending = [i for i in c.get("/api/state").json()["pending"]]
    it = next(p for p in pending)
    assert it["status"] == "pending_approval"
    ao = c.post(f"/api/intents/{it['id']}/approval-options", headers=H).json()
    done = c.post(f"/api/intents/{it['id']}/approve", json={"credential": a.get(ao)}, headers=H)
    assert done.status_code == 200 and done.json()["status"] == "executed"
    # single use: the same intent cannot be approved or executed again
    again = c.post(f"/api/intents/{it['id']}/approve", json={"credential": a.get(ao)}, headers=H)
    assert again.status_code == 409


def test_booking_more_than_balance_is_refused_before_approval(monkeypatch):
    from app.ledger import Ledger
    c, _ = register("e2e-broke")
    monkeypatch.setattr(Ledger, "balance_tmon", lambda self: 0.0)
    it = search_and_prepare(c, "Find a hotel in Jaipur tomorrow", idx=-1)       # would normally need a passkey approval
    assert it["status"] == "failed" and "Insufficient balance" in it["error"] and not it["tx_hash"]
    assert c.get("/api/state").json()["pending"] == []
