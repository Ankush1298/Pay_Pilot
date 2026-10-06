"""PayPilot gateway (one instance per user): the only path between the AI and the user's money.

Lifecycle of an intent
  submit -> policy.evaluate -> BLOCK (stop) | STEP_UP (wait for a passkey assertion) | ALLOW
  approve -> WebAuthn assertion over the intent digest -> re-evaluate -> execute
  execute -> mint ledger authorization (HMAC) -> ledger transfer -> merchant booking -> record
"""
from __future__ import annotations

import copy
import hashlib
import secrets
import time

from . import merchants as M
from . import config
from . import passkeys as PK
from .crypto import digest as make_digest, hmac_tag
from .ledger import Ledger, LedgerError
from .policy import PAY_TYPES, STRIKE_RULES, evaluate, inr
from .state import State

DIGEST_FIELDS = ["type", "merchant_domain", "pay_to", "amount", "currency", "purpose", "payload",
                 "expiry", "nonce", "device_id"]


class GatewayError(Exception):
    def __init__(self, status: int, code: str, message: str):
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


class Gateway:
    def __init__(self, user_id: str, username: str, master: bytes, state: dict | None = None, ledger: dict | None = None):
        self.user_id, self.username = user_id, username
        self.st = State(state)
        self._exec_key = hashlib.sha256(master + b"|exec|" + user_id.encode()).digest()   # never leaves this object
        self.wallet = self.st.wallet_address or M.user_addr(user_id)
        self.ledger = Ledger(self._exec_key, self.wallet, ledger)
        self.on_revoke_session = lambda sid: None          # wired by the registry to the auth layer
        self.on_revoke_device = lambda did: None

    def initialize_wallet(self, credential: dict):
        trusted = [m for m in M.REGISTRY.values() if m.get("verified") and m.get("pay_to")]
        self.wallet = self.ledger.initialize_wallet(credential, self.st.policy["per_tx_limit"], self.st.policy["daily_limit"], trusted)
        self.st.wallet_address = self.wallet
        return self.wallet

    def snapshot(self) -> tuple[dict, dict]:
        return self.st.to_dict(), self.ledger.to_dict()

    # ------------------------------------------------------------ devices
    def add_device(self, name: str, ua: str = "", ip: str = "", trusted: bool = False) -> dict:
        st = self.st
        did = "dev_" + secrets.token_hex(4)
        st.devices[did] = {"id": did, "name": (name or "Device")[:40], "status": "trusted" if trusted else "pending",
                           "first_seen": st.now(), "trusted_at": st.now() if trusted else None, "ua": ua[:160], "ip": ip}
        if trusted:
            st.log("device", f"Trusted device registered: '{name}'", "ok")
        else:
            st.alert("warn", f"New device sign-in: '{name}' from {ip or 'unknown location'}. Payments are locked for "
                             f"{st.policy['new_device_lock_hours']}h until you approve or block it.", did)
        return st.devices[did]

    def promote_device(self, device_id: str, why: str):
        d = self.st.devices[device_id]
        d["status"], d["trusted_at"] = "trusted", self.st.now()
        self.st.alert("warn", f"Device '{d['name']}' was trusted using {why}", device_id)

    def ensure_session(self, session_id: str, device_id: str) -> dict:
        s = self.st.sessions.get(session_id)
        if not s:
            s = self.st.sessions[session_id] = {"id": session_id, "device_id": device_id, "status": "active",
                                                "strikes": 0, "created": self.st.now()}
        return s

    def _require_trusted(self, sess: dict) -> dict:
        dev = self.st.devices.get(sess["device_id"])
        if sess.get("status") != "active" or not dev or dev["status"] == "blocked":
            raise GatewayError(403, "not_trusted", "This action is unavailable on this device")
        if dev["status"] == "pending":
            unlock = dev["first_seen"] + self.st.policy["new_device_lock_hours"] * 3600
            if self.st.now() < unlock:
                raise GatewayError(403, "new_device_locked", f"New-device transaction hold is active for {self.st.policy['new_device_lock_hours']} hours")
            # After the hold expires, the passkey used to sign in is enough for STEP_UP actions.
        return dev

    def block_device(self, sess: dict, device_id: str) -> dict:
        """Blocking is the safe direction, so it needs no step-up."""
        st, me = self.st, self._require_trusted(sess)
        tgt = st.devices.get(device_id)
        if not tgt:
            raise GatewayError(404, "no_device", "Unknown device")
        if tgt["id"] == me["id"]:
            raise GatewayError(400, "self_block", "You can't block the device you're using")
        tgt["status"] = "blocked"
        for s in st.sessions.values():
            if s["device_id"] == device_id:
                s["status"] = "terminated"
        self.on_revoke_device(device_id)
        st.alert("crit", f"Device '{tgt['name']}' was blocked and all its sessions ended", device_id)
        return tgt

    def request_device_approval(self, sess: dict, device_id: str) -> dict:
        self._require_trusted(sess)
        return self.submit_intent(sess, origin="user", type="approve_device", amount=0,
                                  purpose=f"Trust device {self.st.devices.get(device_id, {}).get('name', device_id)}",
                                  payload={"device_id": device_id})

    def propose_policy(self, sess: dict, new_policy: dict) -> dict:
        self._require_trusted(sess)
        return self.submit_intent(sess, origin="user", type="change_settings", amount=0,
                                  purpose="Change security policy", payload={"policy": new_policy})

    def initial_policy(self, sess: dict, new_policy: dict) -> dict:
        """First-run setup only: open for 30 minutes after sign-up, before any payment."""
        st = self.st
        if not st.onboarding_open or st.now() - st.created > 1800 or st.executions:
            raise GatewayError(403, "onboarding_closed", "Initial setup is closed. Changes now need biometric approval.")
        self._require_trusted(sess)
        probe = {"type": "change_settings", "origin": "user", "payload": {"policy": new_policy}, "amount": 0,
                 "session_id": sess["id"], "device_id": sess["device_id"], "expiry": st.now() + 60,
                 "nonce": "probe", "pay_to": None}
        if any(r["rule"] == "invalid_policy" for r in evaluate(st, probe, recheck=True)["reasons"]):
            raise GatewayError(422, "invalid_policy", "Those policy values are not valid")
        self._apply_policy(new_policy)
        st.log("policy", "Initial security policy set", "ok")
        return st.policy

    def finish_onboarding(self, sess: dict):
        self._require_trusted(sess)
        self.st.onboarding_open = False

    def _apply_policy(self, p: dict):
        for k, v in p.items():
            self.st.policy[k] = float(v) if k.endswith("_limit") else list(v)

    # ----------------------------------------------------------- passkeys
    def passkey_register_options(self, sess: dict, origin: str, username: str) -> dict:
        self._require_trusted(sess)
        try:
            return PK.registration_options(self.st, self.user_id, username, origin)
        except PK.PasskeyError as e:
            raise GatewayError(400, e.code, e.message)

    def passkey_register_verify(self, sess: dict, origin: str, payload: dict, name: str) -> dict:
        self._require_trusted(sess)
        try:
            cred = PK.verify_registration(self.st, sess["device_id"], origin, payload, name)
        except (PK.PasskeyError, KeyError) as e:
            raise GatewayError(400, getattr(e, "code", "bad_request"), getattr(e, "message", "Malformed passkey data"))
        try:
            tx_hash = self.ledger.add_passkey(cred)
        except LedgerError as e:
            raise GatewayError(503, "passkey_chain_sync_failed", str(e))
        self.st.log("passkey", f"Passkey '{cred['name']}' registered and synced to the smart account", "ok", tx_hash=tx_hash)
        return self._public_cred(cred) | {"tx_hash": tx_hash}

    @staticmethod
    def _public_cred(c: dict) -> dict:
        return {"id": c["id"][:12], "full_id": c["id"], "device_id": c["device_id"], "name": c["name"],
                "created": c["created"], "sign_count": c["sign_count"], "key_id": c.get("key_id")}

    def _device_cred_ids(self, device_id: str) -> list[str]:
        return [c["id"] for c in self.st.credentials.values() if c["device_id"] == device_id]

    def approval_options(self, sess: dict, intent_id: str, origin: str) -> dict:
        st = self.st
        self._require_trusted(sess)
        it = st.intents.get(intent_id)
        if not it or it["status"] != "pending_approval":
            raise GatewayError(409, "not_pending", "Nothing awaiting approval with that id")
        dev = st.devices.get(sess["device_id"])
        if dev and dev["status"] == "pending" and st.now() >= dev["first_seen"] + st.policy["new_device_lock_hours"] * 3600:
            ids = list(st.credentials.keys())  # synced passkeys may live on another platform device
        else:
            ids = self._device_cred_ids(sess["device_id"])
        if not ids:
            raise GatewayError(409, "no_passkey", "Register a passkey before approving transactions")
        challenge = PK.b64u(bytes.fromhex(it["digest"]))      # the signature covers THIS exact transaction
        try:
            return PK.assertion_options(st, origin, ids, challenge)
        except PK.PasskeyError as e:
            raise GatewayError(400, e.code, e.message)

    # ------------------------------------------------------------ intents
    def submit_intent(self, sess: dict, *, origin: str, type: str, merchant_domain: str | None = None,
                      pay_to: str | None = None, amount: float = 0, purpose: str = "",
                      payload: dict | None = None, context: dict | None = None, ttl: int = 600,
                      lab: bool = False) -> dict:
        st = self.st
        payload = copy.deepcopy(payload or {})
        if origin == "agent" and type in PAY_TYPES:
            active = self.st.active_user_intent
            if active and self.st.now() - float(active.get("set_at", 0)) <= 1800:
                context = copy.deepcopy(context or {})
                context["user_intent"] = {k: active.get(k) for k in ("kind", "city", "budget", "units")}
            else:
                context = {**(context or {}), "user_intent": None}

        # Amounts for cancel/modify are derived by the server from the booking, never taken from the caller.
        if type in {"cancel_booking", "modify_booking"}:
            b = st.bookings.get(payload.get("booking_id"))
            if not b or b["status"] != "confirmed":
                raise GatewayError(404, "no_booking", "Booking not found or not active")
            merchant_domain = b["merchant_domain"]
            if type == "cancel_booking":
                amount, pay_to, purpose = b["amount"], b["payer"], f"Cancel & refund: {b['title']}"
            else:
                try:
                    units = int(payload.get("units", b["units"]))
                except (TypeError, ValueError):
                    raise GatewayError(400, "bad_units", "Quantity must be a number")
                if units < 1 or units == b["units"] or units > 30:
                    raise GatewayError(400, "bad_units", "Choose a different quantity between 1 and 30")
                payload["units"] = units
                delta = (units - b["units"]) * b["unit_price"]
                amount, pay_to = abs(delta), (b["pay_to"] if delta > 0 else b["payer"])
                payload["delta"] = delta
                purpose = f"Change {b['title']} from {b['units']} to {units} {b['unit_label']}(s)"

        rec = M.resolve(merchant_domain)
        it = {
            "id": "int_" + secrets.token_hex(5), "type": type, "origin": origin, "lab": lab,
            "merchant_domain": merchant_domain, "merchant_name": rec["name"] if rec else merchant_domain,
            "pay_to": pay_to, "amount": round(float(amount), 2), "currency": "INR", "purpose": purpose,
            "payload": payload, "context": context or {}, "session_id": sess["id"],
            "device_id": sess["device_id"], "created_at": st.now(), "expiry": round(st.now() + ttl, 3),
            "nonce": secrets.token_hex(8), "status": "new", "tx_hash": None, "booking_id": None,
        }
        it["digest"] = make_digest({k: it[k] for k in DIGEST_FIELDS})
        st.intents[it["id"]] = it

        decision = evaluate(st, it)
        it["decision"] = decision
        tag = "[SECURITY LAB] " if lab else ""
        label = f"{tag}{origin} → {type.replace('_', ' ')} {inr(it['amount'])} → {it['merchant_name'] or it['pay_to']}"

        if decision["verdict"] == "BLOCK":
            it["status"] = "blocked"
            st.log("intent", f"BLOCKED: {label}", "crit", intent_id=it["id"])
            if not lab or sess.get("lab"):
                self._maybe_strike(sess, decision)
        else:
            st.nonces.add(it["nonce"])
            if decision["verdict"] == "STEP_UP":
                it["status"] = "pending_approval"
                st.log("intent", f"NEEDS VERIFICATION: {label}", "warn", intent_id=it["id"])
                if not lab:
                    st.alert("info", f"Approval needed: {inr(it['amount'])} {it['purpose']}" if it["amount"]
                             else f"Approval needed: {it['purpose']}", sess["device_id"])
            else:
                it["status"] = "approved"
                st.log("intent", f"AUTO-APPROVED: {label}", "ok", intent_id=it["id"])
                self._execute(it)
        return it

    def _maybe_strike(self, sess: dict, decision: dict):
        st = self.st
        if not any(r["rule"] in STRIKE_RULES for r in decision["reasons"] if r["severity"] == "block"):
            return
        sess["strikes"] = sess.get("strikes", 0) + 1
        if sess["strikes"] >= st.policy["strike_limit"] and sess["status"] == "active":
            sess["status"] = "terminated"
            if sess.get("lab"):
                return                                   # sandbox session: no account-level effects
            dev = st.devices.get(sess["device_id"])
            if dev and dev["status"] == "pending":
                dev["status"] = "blocked"
                self.on_revoke_device(dev["id"])
            self.on_revoke_session(sess["id"])
            st.alert("crit", f"Repeated suspicious attempts: session ended"
                             f"{' and the device was blocked' if dev and dev['status'] == 'blocked' else ''}. "
                             "Sign in again with a discoverable passkey to continue.",
                     sess["device_id"])

    def approve(self, sess: dict, intent_id: str, origin: str, credential: dict) -> dict:
        st = self.st
        signer = self._require_trusted(sess)
        it = st.intents.get(intent_id)
        if not it:
            raise GatewayError(404, "no_intent", "Unknown intent")
        if it["status"] != "pending_approval":
            raise GatewayError(409, "not_pending", f"Intent is {it['status']}, not awaiting approval")
        if it["expiry"] <= st.now():
            it["status"] = "expired"
            st.log("intent", f"Approval window expired for {it['id']}", "warn", intent_id=it["id"])
            raise GatewayError(410, "expired", "Approval window expired; ask the assistant to prepare it again")
        if it["type"] == "approve_device" and it["payload"].get("device_id") == signer["id"]:
            raise GatewayError(403, "self_approval", "A device cannot approve itself")
        try:
            dev = st.devices.get(signer["id"])
            allowed = list(st.credentials.keys()) if (dev and dev["status"] == "pending") else self._device_cred_ids(signer["id"])
            PK.verify_assertion(st, origin, credential or {}, PK.b64u(bytes.fromhex(it["digest"])), allowed)
        except (PK.PasskeyError, KeyError, TypeError) as e:
            st.log("approval", f"Rejected invalid passkey assertion for {it['id']}", "crit", intent_id=it["id"])
            raise GatewayError(403, getattr(e, "code", "bad_assertion"),
                               getattr(e, "message", "Malformed passkey response"))
        again = evaluate(st, it, recheck=True)             # hard blocks can still appear while it waited
        if again["verdict"] == "BLOCK":
            it["status"], it["decision"] = "blocked", again
            st.log("intent", f"BLOCKED on re-check: {it['id']}", "crit", intent_id=it["id"])
            return it
        it["status"], it["approved_by"] = "approved", signer["id"]
        it["passkey_data"] = copy.deepcopy(credential)
        cred_id = credential.get("id")
        if cred_id in st.credentials:
            it["passkey_data"]["key_id"] = st.credentials[cred_id].get("key_id")
        st.log("approval", f"Approved {it['id']} with the passkey of '{signer['name']}' (digest {it['digest'][:10]}…)",
               "ok", intent_id=it["id"])
        self._execute(it)
        return it

    def reject(self, sess: dict, intent_id: str) -> dict:
        self._require_trusted(sess)
        it = self.st.intents.get(intent_id)
        if not it or it["status"] != "pending_approval":
            raise GatewayError(409, "not_pending", "Nothing to reject")
        it["status"] = "rejected"
        self.st.log("approval", f"Rejected {it['id']}", "warn", intent_id=it["id"])
        return it

    # ------------------------------------------------------- connections
    def connect_start(self, sess: dict, domain: str) -> str:
        self._require_trusted(sess)
        rec = M.resolve(domain)
        if not rec or not rec["verified"]:
            raise GatewayError(400, "not_connectable", "Only verified merchants can be connected")
        state = PK.new_challenge(self.st, "connect:" + domain, ttl=600)
        return f"/merchant/{domain}/authorize?state={state}"

    def connect_finish(self, sess: dict, domain: str, state: str, code: str):
        self._require_trusted(sess)
        ch = self.st.challenges.pop(state, None)
        if not ch or ch["purpose"] != "connect:" + domain or ch["exp"] < time.time():
            raise GatewayError(400, "bad_state", "Connection request expired. Start again.")
        got = M.exchange_code(domain, code)
        if not got:
            raise GatewayError(400, "bad_code", "The merchant did not confirm the sign-in")
        self.st.connections[domain] = {"domain": domain, "member": got["member"], "token": got["token"],
                                       "scope": "search, book", "connected_at": self.st.now()}
        self.st.log("connection", f"Connected {domain} as '{got['member']}' (delegated session, no password shared)", "ok")

    def disconnect(self, sess: dict, domain: str):
        self._require_trusted(sess)
        c = self.st.connections.pop(domain, None)
        if c:
            M.revoke_token(c["token"])
            self.st.log("connection", f"Disconnected {domain}; token revoked", "warn")

    # ---------------------------------------------------------- execution
    def _execute(self, it: dict):
        """Only called after a policy decision. Mints the ledger authorization."""
        st, t = self.st, it["type"]
        auth = hmac_tag(self._exec_key, it["digest"])
        try:
            if t in PAY_TYPES or t == "p2p_transfer":
                tx = self.ledger.transfer(auth, it["digest"], self.wallet, it["pay_to"], it["amount"], it["purpose"],
                                          intent_data=it, passkey_data=it.get("passkey_data"))
                it["tx_hash"] = tx["tx_hash"]
                st.executions.append({"ts": st.now(), "amount": it["amount"], "type": t})
                st.onboarding_open = False
                if t in PAY_TYPES:
                    p = it["payload"]
                    conn = st.connections.get(it["merchant_domain"])
                    mb = M.book_with_token(it["merchant_domain"], conn["token"] if conn else None, it["purpose"])
                    bid = "bk_" + secrets.token_hex(4)
                    st.bookings[bid] = {
                        "id": bid, "intent_id": it["id"], "kind": t, "merchant_domain": it["merchant_domain"],
                        "merchant_name": it["merchant_name"], "title": p.get("title", it["purpose"]),
                        "city": p.get("city"), "units": p.get("units", 1), "unit_price": p.get("unit_price", it["amount"]),
                        "unit_label": p.get("unit_label", "unit"), "amount": it["amount"], "payer": self.wallet,
                        "pay_to": it["pay_to"], "status": "confirmed", "tx_hash": tx["tx_hash"],
                        "confirmation": mb["confirmation"], "booked_as": mb["booked_as"], "created_at": st.now(),
                    }
                    it["booking_id"] = bid
            elif t == "cancel_booking":
                b = st.bookings[it["payload"]["booking_id"]]
                # A real merchant refund must be initiated by the merchant/payment rail, not by the user's wallet.
                # The demo records the cancellation only; the mock merchant can expose a refund in test mode.
                if getattr(self.ledger, "network", "") == "simulated":
                    tx = self.ledger.transfer(auth, it["digest"], b["pay_to"], b["payer"], it["amount"],
                                              "refund " + b["id"], allow_overdraft=True, intent_data=it, passkey_data=it.get("passkey_data"))
                    it["tx_hash"] = tx["tx_hash"]
                b["status"] = "cancelled"
            elif t == "modify_booking":
                b = st.bookings[it["payload"]["booking_id"]]
                delta = it["payload"]["delta"]
                if delta > 0:
                    # Additional payment comes from the user's smart account.
                    tx = self.ledger.transfer(auth, it["digest"], self.wallet, b["pay_to"], it["amount"],
                                              "modify " + b["id"], intent_data=it, passkey_data=it.get("passkey_data"))
                    it["tx_hash"] = tx["tx_hash"]
                    st.executions.append({"ts": st.now(), "amount": it["amount"], "type": t})
                b["units"], b["amount"] = int(it["payload"]["units"]), b["amount"] + delta
            elif t == "change_settings":
                newp = it["payload"]["policy"]
                self._apply_policy(newp)
                self.ledger.set_policy(int(self.st.policy["per_tx_limit"]), int(self.st.policy["daily_limit"]), it.get("passkey_data"), it["digest"])
            elif t == "approve_device":
                d = st.devices[it["payload"]["device_id"]]
                d["status"], d["trusted_at"] = "trusted", st.now()
                st.alert("ok", f"Device '{d['name']}' approved by you and is now trusted. Add a passkey on it to approve payments.", d["id"])
            it["status"] = "executed"
            st.log("execute", f"Executed {it['id']}" + (f" tx {it['tx_hash'][:12]}…" if it["tx_hash"] else ""),
                   "ok", intent_id=it["id"])
        except LedgerError as e:
            it["status"], it["error"] = "failed", str(e)
            st.log("execute", f"Ledger refused {it['id']}: {e}", "crit", intent_id=it["id"])

    # -------------------------------------------------------------- views
    def public_state(self, sess: dict) -> dict:
        st = self.st
        dev = st.devices.get(sess["device_id"])
        pub = lambda d: {k: v for k, v in d.items() if k not in {"token"}}
        intents = sorted((i for i in st.intents.values() if not i.get("lab")), key=lambda i: -i["created_at"])
        creds = [self._public_cred(c) for c in st.credentials.values()]
        public_policy = {k: v for k, v in st.policy.items() if k not in {"per_tx_limit", "daily_limit", "absolute_cap"}}
        public_policy["configured"] = True
        return {
            "server_time": st.now(), "username": self.username,
            "onboarding_open": st.onboarding_open,
            "me": {"device": dev, "session": sess, "has_passkey": bool(self._device_cred_ids(sess["device_id"]))},
            "policy": public_policy, "devices": list(st.devices.values()), "passkeys": creds,
            "intents": intents[:30], "pending": [i for i in intents if i["status"] == "pending_approval"],
            "bookings": sorted(st.bookings.values(), key=lambda b: -b["created_at"]),
            "connections": [pub(c) for c in st.connections.values()],
            "alerts": list(reversed(st.alerts[-30:])), "audit": list(reversed(st.audit[-80:])),
            "spent_24h": st.spent_since(st.now() - 86400),
            "ledger": {"network": self.ledger.network, "simulated": self.ledger.network == "simulated", "address": self.wallet,
                       "faucet_url": None if self.ledger.network == "simulated" else config.FAUCET_URL,
                       "explorer_url": None if self.ledger.network == "simulated" else config.EXPLORER_URL,
                       "balance_tmon": self.ledger.balance_tmon(),
                       "balance_inr": round(self.ledger.balance_tmon() * 100, 2), "txs": self.ledger.txs[-10:][::-1]},
        }