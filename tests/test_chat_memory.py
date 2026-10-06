"""Conversational memory: persistence, context carry-over, isolation, and the digest guarantee for inferred values."""
from app.crypto import digest as make_digest
from app.gateway import DIGEST_FIELDS
from tests.test_e2e import H, register
from tests.virtual_authenticator import b64u


def say(c, text, cid=None):
    body = {"message": text, **({"conversation_id": cid} if cid else {})}
    r = c.post("/api/agent/chat", json=body, headers=H)
    assert r.status_code == 200, r.text
    return r.json()


def test_city_carries_over_to_followups():
    c, _ = register("mem-carry")
    first = say(c, "find a hotel in Jaipur")
    cid = first["conversation_id"]
    cheapest = say(c, "book the cheapest one", cid)
    assert [o["city"] for o in cheapest["options"]] == ["Jaipur"]
    assert cheapest["options"][0]["total"] == min(o["total"] for o in first["options"])
    assert {"city", "option"} <= {r["field"] for r in cheapest["resolved"]}
    weekend = say(c, "what about next weekend?", cid)
    assert weekend["context"]["city"] == "Jaipur" and weekend["context"]["dates"]["text"] == "next weekend"
    assert all(o["city"] == "Jaipur" for o in weekend["options"]) and weekend["options"]


def test_newest_value_overrides_and_budget_is_remembered():
    c, _ = register("mem-override")
    r1 = say(c, "find a hotel in Jaipur under 1000")
    cid = r1["conversation_id"]
    r2 = say(c, "actually Goa", cid)
    assert r2["context"]["city"] == "Goa" and r2["context"]["budget"] == 1000 and r2["options"]
    assert all(o["city"] == "Goa" and o["unit_price"] <= 1000 for o in r2["options"])
    assert say(c, "under 2000 instead", cid)["context"]["budget"] == 2000


def test_new_chat_does_not_inherit_context_and_asks_instead_of_guessing():
    c, _ = register("mem-newchat")
    say(c, "find a hotel in Jaipur")
    fresh = c.post("/api/chat/conversations", headers=H).json()
    assert fresh["context"] == {}
    reply = say(c, "book the cheapest one", fresh["id"])
    assert reply["options"] == [] and reply["needs"] == "kind"
    assert say(c, "find a hotel", fresh["id"])["needs"] == "city"          # never defaults to Jaipur
    assert "Jaipur" not in str(say(c, "hello")["context"])


def test_two_users_never_see_each_others_history():
    ca, _ = register("mem-alice")
    cb, _ = register("mem-bob")
    cid = say(ca, "find a hotel in Goa")["conversation_id"]
    assert cb.get("/api/chat/conversations", headers=H).json() == []
    for call in (lambda: cb.get(f"/api/chat/conversations/{cid}"),
                 lambda: cb.patch(f"/api/chat/conversations/{cid}/context", json={"context": {"city": "Delhi"}}, headers=H),
                 lambda: cb.delete(f"/api/chat/conversations/{cid}", headers=H),
                 lambda: cb.post("/api/agent/chat", json={"message": "hi", "conversation_id": cid}, headers=H)):
        assert call().status_code == 404
    assert ca.get(f"/api/chat/conversations/{cid}").json()["context"]["city"] == "Goa"


def test_history_survives_logout_and_login():
    c, a = register("mem-persist")
    cid = say(c, "find a hotel in Jaipur")["conversation_id"]
    c.post("/api/auth/logout", headers=H)
    lo = c.post("/api/auth/login/options", headers=H).json()
    assert c.post("/api/auth/login/verify", json={"credential": a.get(lo)}, headers=H).status_code == 200
    conv = c.get(f"/api/chat/conversations/{cid}").json()
    assert [m["role"] for m in conv["messages"]] == ["user", "agent"] and conv["context"]["city"] == "Jaipur"
    assert c.get("/api/chat/conversations").json()[0]["id"] == cid


def test_chip_edits_validate_and_apply_to_next_message():
    c, _ = register("mem-chips")
    cid = say(c, "find a hotel in Jaipur under 1000")["conversation_id"]
    url = f"/api/chat/conversations/{cid}/context"
    assert c.patch(url, json={"context": {"budget": -5}}, headers=H).status_code == 422
    assert c.patch(url, json={"context": {"kind": "movie"}}, headers=H).status_code == 422
    ctx = c.patch(url, json={"context": {"city": "goa", "budget": None}}, headers=H).json()
    assert ctx["city"] == "Goa" and "budget" not in ctx
    nxt = say(c, "show me options", cid)
    assert nxt["context"]["city"] == "Goa" and all(o["city"] == "Goa" for o in nxt["options"])


# ---------------------------------------------------------------- the security guarantee
def prepare_cheapest_from_context(c):
    cid = say(c, "find a hotel in Jaipur")["conversation_id"]
    opt = say(c, "book the cheapest one", cid)["options"][0]
    return cid, c.post("/api/agent/prepare", json={"option_id": opt["id"], "conversation_id": cid}, headers=H).json()


def test_context_filled_intent_is_never_auto_approved_and_shows_what_was_inferred():
    c, _ = register("mem-stepup")
    cid, it = prepare_cheapest_from_context(c)
    assert it["amount"] <= 1500                                            # cheap enough to auto-approve if it were explicit
    assert it["status"] == "pending_approval" and it["decision"]["verdict"] == "STEP_UP"
    assert "context_inferred" in {r["rule"] for r in it["decision"]["reasons"]}
    inferred = {r["field"] for r in it["payload"]["resolved_from_context"]}
    assert {"city", "option"} <= inferred


def test_digest_covers_inferred_values_and_matches_what_is_signed_and_settled():
    c, a = register("mem-digest")
    cid, it = prepare_cheapest_from_context(c)
    assert make_digest({k: it[k] for k in DIGEST_FIELDS}) == it["digest"]          # inferred fields are inside the digest
    tampered = {**{k: it[k] for k in DIGEST_FIELDS}, "payload": {**it["payload"], "resolved_from_context": []}}
    assert make_digest(tampered) != it["digest"]
    ao = c.post(f"/api/intents/{it['id']}/approval-options", headers=H).json()
    assert ao["challenge"] == b64u(bytes.fromhex(it["digest"]))                    # the passkey signs exactly this digest
    # Editing the chat context afterwards must not change what the user is approving
    c.patch(f"/api/chat/conversations/{cid}/context", json={"context": {"city": "Goa"}}, headers=H)
    pending = c.get("/api/state").json()["pending"][0]
    assert pending["digest"] == it["digest"] and pending["payload"]["city"] == "Jaipur"
    done = c.post(f"/api/intents/{it['id']}/approve", json={"credential": a.get(ao)}, headers=H).json()
    assert done["status"] == "executed" and done["digest"] == it["digest"]
    assert c.get("/api/state").json()["ledger"]["txs"][0]["digest"] == it["digest"]


def test_fully_explicit_request_still_auto_approves():
    c, _ = register("mem-explicit")
    opt = say(c, "find a hotel in Jaipur under 1000")["options"][0]
    it = c.post("/api/agent/prepare", json={"option_id": opt["id"]}, headers=H).json()
    assert it["status"] == "executed" and "resolved_from_context" not in it["payload"]
