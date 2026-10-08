"""Conversation memory: pull explicit values out of a message and merge them into the chat's context.

Rules (security-relevant):
  * The newest explicit value always overrides the old one.
  * A value that was NOT stated in this message but is used because of the context is reported in `resolved`.
    That list travels inside the intent payload (so it is covered by the digest) and forces a step-up, so an
    inferred value can never be approved silently.
  * Missing required values are asked for, never guessed.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from . import merchants as M

KNOWN_CITIES = {"jaipur": "Jaipur", "goa": "Goa", "delhi": "Delhi", "mumbai": "Mumbai", "bengaluru": "Bengaluru",
                "bangalore": "Bengaluru", "chennai": "Chennai", "kolkata": "Kolkata", "udaipur": "Udaipur",
                "hyderabad": "Hyderabad", "pune": "Pune"}
MOVIE_WORDS = ("movie", "film", "cinema", "ticket", "show")
HOTEL_WORDS = ("hotel", "stay", "room", "resort", "night", "lodge")
MONTHS = {m: i + 1 for i, m in enumerate(["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"])}
CONTEXT_KEYS = ("kind", "city", "dates", "budget", "guests", "units", "merchant", "currency", "last_selected")
EDITABLE = ("city", "dates", "budget", "guests", "merchant")
WEEKDAYS = {w: i for i, w in enumerate(["mon", "tue", "wed", "thu", "fri", "sat", "sun"])}
_MON = r"(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"


def _next_weekday(today: dt.date, wd: int, skip_today: bool = False) -> dt.date:
    d = (wd - today.weekday()) % 7
    return today + dt.timedelta(days=d or (7 if skip_today else 0))


def _date(day: int, mon: str, today: dt.date) -> dt.date | None:
    try:
        d = dt.date(today.year, MONTHS[mon[:3]], day)
    except (ValueError, KeyError):
        return None
    return d if d >= today else d.replace(year=today.year + 1)


def parse_dates(q: str, today: dt.date) -> dict | None:
    q = q.lower()
    iso = re.findall(r"\b(\d{4}-\d{2}-\d{2})\b", q)
    try:
        if iso:
            s = dt.date.fromisoformat(iso[0]); e = dt.date.fromisoformat(iso[1]) if len(iso) > 1 else None
            return {"text": " to ".join(iso[:2]), "start": s.isoformat(), "end": e.isoformat() if e else None}
    except ValueError:
        return None
    # "15-18 oct", "15 to 18 oct", "oct 15-18": one month shared by both days
    _SEP = r"\s*(?:-|\u2013|\u2014|to|until|till|through)\s*"
    rng = re.search(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?{_SEP}(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON}\b", q)
    if rng:
        d1, d2, mon = int(rng.group(1)), int(rng.group(2)), rng.group(3)
    elif rng := re.search(rf"\b{_MON}\s+(\d{{1,2}})(?:st|nd|rd|th)?{_SEP}(\d{{1,2}})(?:st|nd|rd|th)?\b", q):
        mon, d1, d2 = rng.group(1), int(rng.group(2)), int(rng.group(3))
    if rng and (a := _date(d1, mon, today)) and (b := _date(d2, mon, today)) and a < b:
        return {"text": f"{a:%d %b} to {b:%d %b}", "start": a.isoformat(), "end": b.isoformat()}
    found = [(int(m.group(1)), m.group(2)) for m in re.finditer(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+{_MON}\b", q)]
    found += [(int(m.group(2)), m.group(1)) for m in re.finditer(rf"\b{_MON}\s+(\d{{1,2}})\b", q)]
    ds = [d for d in (_date(day, mon, today) for day, mon in found[:2]) if d]
    if ds:
        ds.sort()
        return {"text": " to ".join(f"{d:%d %b}" for d in ds), "start": ds[0].isoformat(),
                "end": ds[1].isoformat() if len(ds) > 1 else None}
    if "day after tomorrow" in q:
        d = today + dt.timedelta(days=2); return {"text": "day after tomorrow", "start": d.isoformat(), "end": None}
    if "tomorrow" in q:
        d = today + dt.timedelta(days=1); return {"text": "tomorrow", "start": d.isoformat(), "end": None}
    if re.search(r"\btoday\b|\btonight\b", q):
        return {"text": "today", "start": today.isoformat(), "end": None}
    m = re.search(r"\b(this|next) weekend\b", q)
    if m:
        sat = _next_weekday(today, 5) + dt.timedelta(days=7 if m.group(1) == "next" else 0)
        return {"text": f"{m.group(1)} weekend", "start": sat.isoformat(), "end": (sat + dt.timedelta(days=1)).isoformat()}
    if "next week" in q:
        d = _next_weekday(today, 0, skip_today=True); return {"text": "next week", "start": d.isoformat(), "end": None}
    m = re.search(r"\b(?:(this|next|on)\s+)?(mon|tues?|wed(?:nes)?|thu(?:rs)?|fri|sat(?:ur)?|sun)(?:day)?\b", q)
    if m:
        d = _next_weekday(today, WEEKDAYS[m.group(2)[:3]], skip_today=True)
        if m.group(1) == "next" and (d - today).days < 7:
            d += dt.timedelta(days=7)
        return {"text": f"{d:%A %d %b}", "start": d.isoformat(), "end": None}
    return None


def parse_message(msg: str, today: dt.date | None = None) -> dict[str, Any]:
    """Only values the user actually stated in this message."""
    today = today or dt.date.today()
    q = msg.lower()
    out: dict[str, Any] = {}
    movie, hotel = any(w in q for w in MOVIE_WORDS), any(w in q for w in HOTEL_WORDS)
    if movie and not hotel:
        out["kind"] = "movie"
    elif hotel:
        out["kind"] = "hotel"
    for name, canon in KNOWN_CITIES.items():
        if re.search(rf"\b{name}\b", q):
            out["city"] = canon
    if m := re.search(r"(\d+)\s*(?:night|day)", q):
        out["units"] = min(int(m.group(1)), 30) or 1
    elif m := re.search(r"(\d+)\s*(?:ticket|seat)", q):
        out["units"] = min(int(m.group(1)), 30) or 1
    if m := re.search(r"(\d+)\s*(?:guest|people|person|adult|pax)", q):
        out["guests"] = min(int(m.group(1)), 20) or 1
    if m := re.search(r"(?:under|below|within|budget(?: of)?|max|upto|up to)\s*(?:₹|rs\.?|inr)?\s*(\d[\d,]*)", q):
        out["budget"] = float(m.group(1).replace(",", ""))
    if d := parse_dates(q, today):
        out["dates"] = d
        # "15th oct to 18th oct" = 3 nights. An explicit "N nights" in the same message still wins.
        if "units" not in out and d.get("end") and not (movie and not hotel):
            nights = (dt.date.fromisoformat(d["end"]) - dt.date.fromisoformat(d["start"])).days
            if nights >= 1:
                out["units"] = min(nights, 30)
    for dom in M.REGISTRY:
        if re.search(rf"\b{re.escape(dom.split('.')[0])}\b", q):
            out["merchant"] = dom
    if re.search(r"₹|\brs\.?\b|\binr\b|rupee", q):
        out["currency"] = "INR"
    if u := re.search(r"https?://([^\s/]+)", msg):
        out["url_domain"] = u.group(1).lower()
    # "book the cheapest one", "the second option": a reference to the previous results, not a new search
    if re.search(r"\b(book|reserve|take|pick|choose|select|go with)\b|\bthe (cheapest|best|first|second|third|last)\b", q):
        if re.search(r"cheapest|lowest|least expensive", q):
            out["_select"] = "cheapest"
        elif re.search(r"\bbest\b|top rated|highest rated", q):
            out["_select"] = "best"
        elif m := re.search(r"\b(first|1st|second|2nd|third|3rd|last)\b", q):
            out["_select"] = {"first": 0, "1st": 0, "second": 1, "2nd": 1, "third": 2, "3rd": 2, "last": -1}[m.group(1)]
    return out


def merge(ctx: dict, explicit: dict) -> dict:
    """Newest explicit value wins. Private (underscore) and per-message keys are not stored."""
    new = {k: v for k, v in ctx.items() if k in CONTEXT_KEYS}
    for k, v in explicit.items():
        if k in CONTEXT_KEYS:
            new[k] = v
    new.setdefault("currency", "INR")
    return new


def rebuild(history: list[dict], today: dt.date | None = None) -> dict:
    """Recover a context from stored user messages (for conversations saved before context existed)."""
    ctx: dict = {}
    for m in history:
        if m.get("role") == "user":
            ctx = merge(ctx, parse_message(m["content"], today))
    return ctx


def validate_edit(updates: dict, today: dt.date | None = None) -> dict:
    """Chip edits from the UI. None clears a value. Raises ValueError on anything invalid."""
    clean: dict[str, Any] = {}
    for k, v in updates.items():
        if k not in EDITABLE:
            raise ValueError(f"'{k}' cannot be edited")
        if v is None:
            clean[k] = None
        elif k == "city":
            if not isinstance(v, str) or not 1 <= len(v.strip()) <= 40:
                raise ValueError("Invalid city")
            clean[k] = KNOWN_CITIES.get(v.strip().lower(), v.strip().title())
        elif k == "budget":
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 < v <= 1_000_000:
                raise ValueError("Invalid budget")
            clean[k] = float(v)
        elif k == "guests":
            if isinstance(v, bool) or not isinstance(v, int) or not 1 <= v <= 20:
                raise ValueError("Invalid guests")
            clean[k] = v
        elif k == "merchant":
            if not isinstance(v, str) or not M.resolve(v):
                raise ValueError("Unknown merchant")
            clean[k] = M.normalize(v)
        elif k == "dates":
            d = parse_dates(v, today or dt.date.today()) if isinstance(v, str) else None
            if not d:
                raise ValueError("Could not understand those dates")
            clean[k] = d
    return clean
