"""Security lab: pre-scripted attack scenarios for the interactive demo.

Each scenario runs inside a sandboxed session (lab=True) so strikes don't
affect the real account. The lab session is separate from the user's real session.
"""
from __future__ import annotations

import secrets

from . import config
from .gateway import Gateway, GatewayError
from .ledger import MockLedger
from . import merchants as M

SCENARIOS: dict[str, tuple[str, str]] = {
    "auto_approve": (
        "Low-risk auto-approval",
        "The agent books a ₹800 hotel on a trusted device within limits. "
        "Policy auto-approves: no friction needed for safe actions.",
    ),
    "step_up": (
        "Step-up verification",
        "The agent tries to book the ₹2,400 Maharaja Suites. "
        "Amount exceeds the ₹1,500 per-transaction limit, so the policy engine demands a passkey signature.",
    ),
    "compromised_ai": (
        "Compromised AI blocked",
        "A prompt-injected page tells the agent to redirect payment to an attacker's wallet. "
        "The policy engine checks the registered payout address and blocks it.",
    ),
    "new_device": (
        "New device lockout",
        "A new device logs in. Payments are locked for 24 h until the owner approves or blocks it.",
    ),
    "lookalike": (
        "Lookalike domain blocked",
        "The agent tries to book via 'grandstay-hotels.mock' which imitates the verified 'grandstay.mock'. "
        "Lookalike detection blocks it immediately.",
    ),
    "daily_limit": (
        "Daily spend limit",
        "With the per-transaction ceiling raised to ₹2,500 for this demo, two ₹2,400 bookings pass; "
        "the third pushes 24 h spend over the ₹5,000 daily limit and triggers a step-up.",
    ),
    "velocity": (
        "Velocity limit",
        "Three payments in quick succession hit the velocity cap. "
        "The fourth triggers a step-up even if each individual amount is small.",
    ),
}


def _sandbox() -> tuple[Gateway, dict]:
    """A throwaway gateway with a simulated ledger: lab attacks can never touch the real account,
    its limits, devices, ledger or the user's active intent."""
    sb = Gateway("lab_" + secrets.token_hex(6), "lab", config.MASTER_KEY)
    sb.ledger = MockLedger(sb._exec_key, sb.wallet)
    dev = sb.add_device("Lab laptop", trusted=True)
    sess = sb.ensure_session("lab_" + secrets.token_hex(6), dev["id"])
    sess["lab"] = True
    sb.st.active_user_intent = {"kind": "hotel", "budget": 10000, "set_at": sb.st.now()}
    return sb, sess


def run(real_gw: Gateway, real_sess: dict, user_id: str, scenario: str) -> dict:
    if scenario not in SCENARIOS:
        raise GatewayError(404, "no_scenario", f"Unknown scenario '{scenario}'")

    gw, lab = _sandbox()
    steps: list[dict] = []

    def step(label: str, fn):
        try:
            result = fn()
            steps.append({"label": label, "status": "ok", "result": result})
            return result
        except GatewayError as e:
            steps.append({"label": label, "status": "blocked",
                          "code": e.code, "message": e.message})
            return None

    def with_intent(fn):
        return fn()

    if scenario == "auto_approve":
        it = step("Agent submits ₹800 hotel booking",
                  lambda: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                           merchant_domain="grandstay.mock",
                                           pay_to=M.addr("grandstay"), amount=800,
                                           purpose="Pink City Residency (1 night, Jaipur)",
                                           payload={"title": "Pink City Residency", "city": "Jaipur",
                                                    "units": 1, "unit_price": 800, "unit_label": "night"},
                                           lab=True)))
        if it:
            steps.append({"label": "Policy verdict", "status": "ok",
                          "result": {"verdict": it["decision"]["verdict"], "reasons": it["decision"]["reasons"]}})

    elif scenario == "step_up":
        it = step("Agent submits ₹2,400 luxury hotel",
                  lambda: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                           merchant_domain="royalpalace.mock",
                                           pay_to=M.addr("royalpalace"), amount=2400,
                                           purpose="Maharaja Suites (1 night, Jaipur)",
                                           payload={"title": "Maharaja Suites", "city": "Jaipur",
                                                    "units": 1, "unit_price": 2400, "unit_label": "night"},
                                           lab=True)))
        if it:
            steps.append({"label": "Policy verdict", "status": "step_up",
                          "result": {"verdict": it["decision"]["verdict"], "reasons": it["decision"]["reasons"]}})

    elif scenario == "compromised_ai":
        step("Compromised agent submits payment to attacker's address",
             lambda: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                      merchant_domain="lucky-stays.example",
                                      pay_to=M.ATTACKER_ADDR, amount=499,
                                      purpose="Amber Fort View (1 night, Jaipur)",
                                      payload={"title": "Amber Fort View", "city": "Jaipur",
                                               "units": 1, "unit_price": 499, "unit_label": "night"},
                                      context={"injection_suspected": True}, lab=True)))

    elif scenario == "new_device":
        # Show what the policy does for a pending device
        nd = gw.add_device("Lab Device (pending)", ua="lab", ip="127.0.0.1", trusted=False)
        nd_sid = "lab_nd_" + secrets.token_hex(6)
        nd_sess = gw.ensure_session(nd_sid, nd["id"])
        nd_sess["lab"] = True
        step("New device tries to book a hotel",
             lambda: with_intent(lambda: gw.submit_intent(nd_sess, origin="agent", type="hotel",
                                      merchant_domain="grandstay.mock",
                                      pay_to=M.addr("grandstay"), amount=800,
                                      purpose="Connaught Central (1 night, Delhi)",
                                      lab=True)))
        steps.append({"label": "Device status", "status": "info",
                      "result": {"device": nd, "message": "Payments locked for 24 h until owner approves"}})

    elif scenario == "lookalike":
        step("Agent submits booking to lookalike domain 'grandstay-hotels.mock'",
             lambda: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                      merchant_domain="grandstay-hotels.mock",
                                      pay_to=M.addr("grandstay-hotels"), amount=800,
                                      purpose="Fake hotel on lookalike domain",
                                      lab=True)))

    elif scenario == "daily_limit":
        # Per-transaction ceiling raised to ₹2,500 (sandbox only) so two big bookings pass and the third trips the daily cap
        gw.st.policy["per_tx_limit"] = 2500
        for i, (title, amount) in enumerate([("Booking 1", 2400), ("Booking 2", 2400), ("Booking 3 – triggers daily limit", 1000)], 1):
            step(f"Payment {i}: {title} (₹{amount})",
                 lambda a=amount, t=title: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                                             merchant_domain="grandstay.mock",
                                                             pay_to=M.addr("grandstay"), amount=a,
                                                             purpose=f"{t} (1 night)", lab=True)))

    elif scenario == "velocity":
        for i in range(1, 5):
            step(f"Payment {i}: quick ₹800 booking",
                 lambda: with_intent(lambda: gw.submit_intent(lab, origin="agent", type="hotel",
                                          merchant_domain="cityinn.mock",
                                          pay_to=M.addr("cityinn"), amount=800,
                                          purpose="Rajputana Lodge (1 night, Jaipur)", lab=True)))

    title, story = SCENARIOS[scenario]
    return {"scenario": scenario, "title": title, "story": story, "steps": steps}
