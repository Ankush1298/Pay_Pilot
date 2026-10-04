"""The policy engine: decides ALLOW / STEP_UP / BLOCK for every intent.

Design rules
  1. The AI never decides. It can only *submit* an intent; this module judges it.
  2. Anything the agent reports about itself (e.g. "I saw something suspicious")
     can only RAISE risk, never lower it.
  3. Hard blocks cannot be overridden by approval; step-ups can.
"""
from __future__ import annotations

import datetime
import math

from . import merchants as M

PAY_TYPES = {"hotel", "movie", "restaurant", "flight", "shopping"}
SENSITIVE_TYPES = {"p2p_transfer", "change_settings", "approve_device", "cancel_booking", "modify_booking"}
AGENT_FORBIDDEN = {"change_settings", "approve_device"}
# Rules that indicate hostile behaviour and count toward session termination.
STRIKE_RULES = {"pay_to_mismatch", "device_locked", "device_blocked", "agent_forbidden", "lookalike_domain",
                "replay", "unknown_type", "absolute_cap", "refund_destination_mismatch"}
POLICY_KEYS = {"per_tx_limit", "daily_limit", "allowed_types", "approved_merchants"}


def inr(x: float) -> str:
    return f"₹{x:,.0f}" if float(x).is_integer() else f"₹{x:,.2f}"


def fmt_ts(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts).strftime("%d %b %H:%M")


def evaluate(st, it: dict, recheck: bool = False) -> dict:
    now, pol, t = st.now(), st.policy, it["type"]
    reasons: list[dict] = []

    def add(sev: str, rule: str, msg: str, weight: int):
        reasons.append({"severity": sev, "rule": rule, "message": msg, "weight": weight})

    # ---- who is asking -------------------------------------------------
    sess = st.sessions.get(it["session_id"])
    dev = st.devices.get(it["device_id"])
    if not sess or sess["status"] != "active":
        add("block", "session_inactive", "Session is not active", 40)
    if not dev:
        add("block", "unknown_device", "Unknown device", 50)
    elif dev["status"] == "blocked":
        add("block", "device_blocked", f"Device '{dev['name']}' is blocked", 60)
    elif dev["status"] == "pending":
        unlock = dev["first_seen"] + pol["new_device_lock_hours"] * 3600
        if now < unlock:
            hrs = math.ceil((unlock - now) / 3600)
            add("block", "device_locked",
                f"New device '{dev['name']}' is in its {pol['new_device_lock_hours']}h lock "
                f"(~{hrs}h left). Owner must approve or block it.", 35)
        else:
            add("step_up", "device_restricted",
                "Device was never approved by the owner: restricted, every payment needs verification", 20)
    if it["origin"] == "agent" and t in AGENT_FORBIDDEN:
        add("block", "agent_forbidden", "An AI agent can never change settings or approve devices", 60)

    # ---- is the request itself well-formed? -----------------------------
    if it["expiry"] <= now:
        add("block", "expired", "Intent has expired", 10)
    if not recheck and it["nonce"] in st.nonces:
        add("block", "replay", "Nonce already used (replay)", 50)
    if it["amount"] < 0:
        add("block", "invalid_amount", "Negative amount", 50)
    if t in PAY_TYPES | {"p2p_transfer"} and it["amount"] > pol["absolute_cap"]:
        add("block", "absolute_cap", f"Above the absolute cap of {inr(pol['absolute_cap'])}", 60)

    # ---- what kind of action is it? ------------------------------------
    if t in SENSITIVE_TYPES:
        add("step_up", "sensitive_action", f"'{t.replace('_', ' ')}' always needs strong verification", 30)
    elif t in PAY_TYPES:
        if t not in pol["allowed_types"]:
            add("block", "type_not_permitted", f"'{t}' payments are not permitted by your policy", 25)
    else:
        add("block", "unknown_type", f"Unknown action type '{t}'", 50)

    # ---- bind agent actions to the user's original intent --------------
    if it["origin"] == "agent" and t in PAY_TYPES:
        ui = (it.get("context") or {}).get("user_intent") or {}
        if ui:
            if ui.get("kind") and ui["kind"] != t:
                add("block", "intent_type_mismatch", "The requested action does not match the user's original task", 70)
            payload = it.get("payload") or {}
            if ui.get("city") and payload.get("city") and ui["city"].lower() != str(payload["city"]).lower():
                add("block", "intent_city_mismatch", "The booking location does not match the user's original task", 60)
            if ui.get("budget") is not None and it["amount"] > float(ui["budget"]):
                add("block", "intent_budget_exceeded", f"This booking exceeds the budget in the user's original request ({inr(float(ui['budget']))})", 75)
        else:
            add("step_up", "intent_unbound", "This agent action has no bound user intent", 30)

    # ---- merchant checks (done here, never trusted from the agent) -----
    if t in PAY_TYPES:
        dom = it.get("merchant_domain")
        rec = M.resolve(dom)
        imitates = M.lookalike(dom) if not rec else None
        if imitates:
            add("block", "lookalike_domain", f"'{dom}' imitates the registered merchant '{imitates}'", 60)
        elif rec is None:
            add("step_up", "unfamiliar_merchant",
                f"Unfamiliar merchant '{dom}' (not in the verified registry): website and payout address "
                "cannot be verified", 30)
        else:
            if not rec["verified"] and rec["domain"] not in pol["approved_merchants"]:
                add("step_up", "unfamiliar_merchant",
                    f"'{rec['name']}' is not a verified merchant and not on your approved list", 30)
            if it["pay_to"].lower() != rec["pay_to"].lower():
                add("block", "pay_to_mismatch",
                    f"Payment address does not match {rec['name']}'s registered payout address", 70)

    # ---- spending rules --------------------------------------------------
    if t in PAY_TYPES or t == "p2p_transfer":
        amt = it["amount"]
        if amt > pol["per_tx_limit"]:
            add("step_up", "over_limit", "This transaction is outside your automatic approval policy and requires strong verification", 25)
        spent = st.spent_since(now - 86400)
        if spent + amt > pol["daily_limit"]:
            add("step_up", "daily_limit",
                "This transaction would exceed your 24h automatic-spend policy", 25)
        if st.count_since(now - pol["velocity_window_s"]) >= pol["velocity_max"]:
            add("step_up", "velocity", "Too many payments in a short time", 20)

    # ---- bookings: refunds/changes ---------------------------------------
    if t in {"cancel_booking", "modify_booking"}:
        b = st.bookings.get((it.get("payload") or {}).get("booking_id"))
        if not b or b["status"] != "confirmed":
            add("block", "no_such_booking", "Booking not found or not active", 20)
        elif t == "cancel_booking" and (it["pay_to"] != b["payer"] or it["amount"] > b["amount"]):
            add("block", "refund_destination_mismatch", "Refunds may only go back to the original payer", 60)

    # ---- device approval / settings changes ------------------------------
    if t == "approve_device":
        tgt = st.devices.get((it.get("payload") or {}).get("device_id"))
        if not tgt or tgt["status"] != "pending":
            add("block", "bad_target", "Device does not exist or is not pending", 20)
    if t == "change_settings":
        newp = (it.get("payload") or {}).get("policy", {})
        try:
            if set(newp) - POLICY_KEYS:
                raise ValueError
            for k in ("per_tx_limit", "daily_limit"):
                if k in newp and not 0 <= float(newp[k]) <= pol["absolute_cap"]:
                    raise ValueError
        except (ValueError, TypeError):
            add("block", "invalid_policy", "Invalid policy values", 20)

    # ---- agent self-reports can only escalate ----------------------------
    if (it.get("context") or {}).get("injection_suspected"):
        add("step_up", "injection_suspected", "The AI reported hidden instructions on the merchant's page", 25)

    order = {"block": 0, "step_up": 1, "info": 2}
    reasons.sort(key=lambda r: (order[r["severity"]], -r["weight"]))   # most decisive reason first
    verdict = "BLOCK" if any(r["severity"] == "block" for r in reasons) else \
        "STEP_UP" if any(r["severity"] == "step_up" for r in reasons) else "ALLOW"
    if verdict == "ALLOW":
        reasons.append({"severity": "info", "rule": "all_checks_passed", "weight": 0,
                        "message": "Trusted device, verified merchant, within all limits"})
    return {"verdict": verdict, "reasons": reasons, "risk": min(100, sum(r["weight"] for r in reasons))}
