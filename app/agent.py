"""The AI agent (sandboxed, rule-based so the demo needs no API key).

What it CAN do: browse merchant pages, compare options, prepare an intent.
What it CANNOT do: sign, hold keys, call the ledger, or decide a payment.

To use a real LLM, replace `chat()`'s parsing/ranking with a model call; keep
`prepare()` exactly as is: it must only ever call `gateway.submit_intent`.
"""
from __future__ import annotations

import re
import secrets
from typing import Any

from . import merchants as M
from .gateway import Gateway, GatewayError

CITIES = ["Jaipur", "Goa", "Delhi"]
MOVIE_WORDS = ("movie", "film", "cinema", "ticket", "show")

# Singleton agent – options are per-user keyed by user_id
_options: dict[str, dict[str, dict]] = {}  # user_id -> {option_id -> option}


def parse(msg: str) -> dict:
    q = msg.lower()
    kind = "movie" if any(w in q for w in MOVIE_WORDS) and "hotel" not in q else "hotel"
    city = next((c for c in CITIES if c.lower() in q), "Jaipur")
    nm = re.search(r"(\d+)\s*(?:night|day)", q)
    tk = re.search(r"(\d+)\s*(?:ticket|seat|people|person)", q)
    bm = re.search(r"(?:under|below|within|budget(?: of)?|max|upto|up to)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)", q)
    um = re.search(r"https?://([^\s/]+)", msg)
    units = int(nm.group(1)) if (nm and kind == "hotel") else int(tk.group(1)) if (tk and kind == "movie") else 1
    return {"kind": kind, "city": city, "units": max(1, units),
            "budget": float(bm.group(1).replace(",", "")) if bm else None,
            "url_domain": um.group(1).lower() if um else None}


class Agent:
    def chat(self, gw: Gateway, user_id: str, message: str) -> dict:
        p = parse(message)
        gw.st.active_user_intent = {**p, "set_at": gw.st.now()}
        browsed, options = [], []
        label = "night" if p["kind"] == "hotel" else "ticket"
        user_opts = _options.setdefault(user_id, {})

        if p["url_domain"] and not M.resolve(p["url_domain"]):
            dom = p["url_domain"]
            browsed.append({"domain": dom, "status": "unknown", "note": "Custom website supplied by the user"})
            opt = self._option(user_opts, p, dom, f"Listing on {dom}", 900, None, None, label,
                               pay_to=M.addr(dom), flags=[])
            options.append(opt)
        else:
            for dom in sorted({i["domain"] for i in M.inventory(p["kind"], p["city"])}):
                page = M.render_page(dom)
                flags = M.scan_text(page)
                injected = M.extract_injected_address(page)
                if flags:
                    note = "Hidden instructions aimed at AI found and ignored: " + "; ".join(flags)
                elif injected:
                    note = "Page contained instructions; flagged as suspicious"
                else:
                    note = "Read listings"
                browsed.append({"domain": dom, "status": "flagged" if (flags or injected) else "ok", "note": note})
                for item in M.inventory(p["kind"], p["city"]):
                    if item["domain"] == dom:
                        options.append(self._option(user_opts, p, dom, item["name"], item["price"], item["rating"],
                                                    item["reviews"], label, flags=flags, injected=injected,
                                                    perks=item["perks"]))

        if p["budget"]:
            options = [o for o in options if o["unit_price"] <= p["budget"]]
        for o in options:
            rec = M.resolve(o["domain"])
            score = (o["rating"] or 3.5) * 10 - o["unit_price"] / 200
            if not rec or not rec["verified"]:
                score -= 15
            if o["flags"]:
                score -= 50
            o["score"] = round(score, 2)
        options.sort(key=lambda o: -o["score"])
        if options:
            options[0]["best"] = True

        if not options:
            text = "I couldn't find anything matching that. Try a higher budget or another city."
        else:
            b = options[0]
            text = (f"I compared {len(options)} option(s) across {len(browsed)} site(s) for {p['units']} "
                    f"{label}(s) in {p['city']}. Best match: {b['title']} at {b['merchant_name']}, "
                    f"₹{b['total']:,.0f} total.")
            flagged = [x for x in browsed if x["status"] == "flagged"]
            if flagged:
                text += f" Warning: {flagged[0]['domain']} hides instructions for AI assistants, so I'm ignoring it."
            if b["flags"] or not (M.resolve(b["domain"]) or {}).get("verified"):
                text += " Note: this merchant is unverified, so you'll be asked to confirm."
        public = [{k: v for k, v in o.items() if not k.startswith("_")} for o in options]
        return {"text": text, "options": public, "browsed": browsed, "query": p}

    def _option(self, user_opts: dict, p, domain, title, unit_price, rating, reviews, label,
                *, pay_to=None, flags=None, injected=None, perks=""):
        rec = M.resolve(domain)
        oid = "opt_" + secrets.token_hex(4)
        opt: dict[str, Any] = {
            "id": oid, "kind": p["kind"], "domain": domain, "merchant_name": rec["name"] if rec else domain,
            "verified": bool(rec and rec["verified"]), "title": title, "city": p["city"], "units": p["units"],
            "unit_label": label, "unit_price": unit_price, "total": unit_price * p["units"],
            "rating": rating, "reviews": reviews, "perks": perks, "flags": flags or [], "best": False,
            "query": dict(p),
            "_pay_to": pay_to or (rec["pay_to"] if rec else M.addr(domain)), "_injected": injected,
        }
        user_opts[oid] = opt
        return opt

    def prepare(self, gw: Gateway, sess: dict, user_id: str, option_id: str) -> dict:
        user_opts = _options.get(user_id, {})
        o = user_opts.get(option_id)
        if not o:
            raise GatewayError(404, "no_option", "Unknown option; search again")
        pay_to = o["_pay_to"]
        ctx: dict[str, Any] = {}
        if o["flags"]:
            ctx["injection_suspected"] = True
        query = o.get("query") or {}
        ctx["user_intent"] = {"kind": query.get("kind", o["kind"]), "city": query.get("city", o["city"]), "budget": query.get("budget")}
        return gw.submit_intent(
            sess, origin="agent", type=o["kind"], merchant_domain=o["domain"], pay_to=pay_to,
            amount=o["total"], purpose=f"{o['title']} ({o['units']} {o['unit_label']}(s), {o['city']})",
            payload={"title": o["title"], "city": o["city"], "units": o["units"],
                     "unit_price": o["unit_price"], "unit_label": o["unit_label"]}, context=ctx)

    def manage_booking(self, gw: Gateway, sess: dict, action: str, booking_id: str,
                       units: int | None = None) -> dict:
        payload: dict[str, Any] = {"booking_id": booking_id}
        if action == "modify":
            payload["units"] = units
        return gw.submit_intent(sess, origin="agent", type=f"{action}_booking", payload=payload)


AGENT = Agent()
