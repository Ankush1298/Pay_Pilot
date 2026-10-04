import base64, hashlib, json
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from app.main import app
from app.registry import REG
from app import auth


def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def make_client(username="tester"):
    c = TestClient(app)
    uid = auth.create_user(username)
    with REG.use(uid) as gw:
        dev = gw.add_device("Trusted laptop", trusted=True)
        token, sid = auth.new_session(uid, dev["id"], "127.0.0.1", "pytest")
        gw.ensure_session(sid, dev["id"])
    c.cookies.set(auth.SESSION_COOKIE, token, path="/")
    c.cookies.set(auth.DEVICE_COOKIE, auth.bind_device(uid, dev["id"]), path="/")
    return c, uid


def test_passkey_registration_and_login_options_are_passwordless():
    c = TestClient(app)
    opts = c.post("/api/auth/register/options", json={"username": "resident-user"})
    assert opts.status_code == 200
    body = opts.json()
    assert body["authenticatorSelection"]["residentKey"] == "required"
    assert body["authenticatorSelection"]["userVerification"] == "required"
    login = c.post("/api/auth/login/options")
    assert login.status_code == 200
    assert "allowCredentials" not in login.json()


def test_auto_approval_under_limit():
    c, _ = make_client("auto_user")
    chat = c.post("/api/agent/chat", json={"message": "Find a hotel in Jaipur under 1000"}).json()
    opt = chat["options"][0]
    result = c.post("/api/agent/prepare", json={"option_id": opt["id"]}).json()
    assert result["status"] == "executed"
    assert result["booking_id"]
    assert result["tx_hash"]


def test_over_limit_requires_step_up():
    c, _ = make_client("stepup_user")
    chat = c.post("/api/agent/chat", json={"message": "Find a hotel in Jaipur under 2400"}).json()
    opt = next(x for x in chat["options"] if x["domain"] == "royalpalace.mock")
    result = c.post("/api/agent/prepare", json={"option_id": opt["id"]}).json()
    assert result["status"] == "pending_approval"
    assert result["decision"]["verdict"] == "STEP_UP"


def test_passkey_approval_no_server_error():
    c, uid = make_client("passkey_user")
    with REG.use(uid) as gw:
        sess = next(iter(gw.st.sessions.values()))
        device_id = sess["device_id"]
        key = ec.generate_private_key(ec.SECP256R1())
        nums = key.public_key().public_numbers()
        cred_id = b64u(b"credential-for-test")
        gw.st.credentials[cred_id] = {
            "id": cred_id, "device_id": device_id, "name": "Test passkey",
            "pub_key_bytes": nums.x.to_bytes(32, "big") + nums.y.to_bytes(32, "big"),
            "pub_x": nums.x.to_bytes(32, "big").hex(), "pub_y": nums.y.to_bytes(32, "big").hex(),
            "key_id": hashlib.sha256(cred_id.encode()).hexdigest(), "sign_count": 0, "created": gw.st.now(),
        }
    chat = c.post("/api/agent/chat", json={"message": "Find a hotel in Jaipur under 2400"}).json()
    opt = next(x for x in chat["options"] if x["domain"] == "royalpalace.mock")
    intent = c.post("/api/agent/prepare", json={"option_id": opt["id"]}).json()
    assert intent["status"] == "pending_approval"
    options = c.post(f"/api/intents/{intent['id']}/approval-options").json()
    challenge = options["challenge"]
    client_data = b64u(json.dumps({"type":"webauthn.get","challenge":challenge,"origin":"http://localhost:3000"}, separators=(",", ":")).encode())
    auth_data = hashlib.sha256(b"localhost").digest() + bytes([0x05]) + (1).to_bytes(4, "big")
    signed = auth_data + hashlib.sha256(base64.urlsafe_b64decode(client_data + "=" * (-len(client_data) % 4))).digest()
    signature = key.sign(signed, ec.ECDSA(hashes.SHA256()))
    credential = {"id": cred_id, "type":"public-key", "response":{"clientDataJSON":client_data,"authenticatorData":b64u(auth_data),"signature":b64u(signature),"userHandle":None}}
    approved = c.post(f"/api/intents/{intent['id']}/approve", json={"credential": credential})
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "executed"


def test_agent_cannot_change_original_budget_or_intent_type():
    c, uid = make_client("intent_binding")
    with REG.use(uid) as gw:
        # A deliberately different option is inserted as if a compromised agent found it earlier.
        from app.agent import AGENT
        AGENT.chat(gw, uid, "Find a hotel in Jaipur under 1500")
        older = AGENT.chat(gw, uid, "Find a hotel in Jaipur under 2400")
        opt = next(x for x in older["options"] if x["domain"] == "royalpalace.mock")
        # Restore the real current user intent to the 1500 request.
        AGENT.chat(gw, uid, "Find a hotel in Jaipur under 1500")
        sess = next(iter(gw.st.sessions.values()))
        result = AGENT.prepare(gw, sess, uid, opt["id"])
    assert result["decision"]["verdict"] == "BLOCK"
    assert any(r["rule"] == "intent_budget_exceeded" for r in result["decision"]["reasons"])
