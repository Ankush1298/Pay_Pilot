"""Per-user wallet/policy snapshots in the `gateways` table (passkeys, policy, devices, audit log, ledger txs).

Saved by the registry after a request that changed that user's state, and loaded when the user's gateway
is first needed (e.g. after a restart). Only the touched user is written, never everyone.
"""
from __future__ import annotations

import json
import time

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.exc import OperationalError

from .db import engine, gateways

_last: dict[str, str] = {}      # user_id -> last saved JSON, so unchanged state costs no write


def _dumps(obj) -> str:
    return json.dumps(obj, default=lambda o: {"__bytes__": o.hex()})   # passkey public keys are raw bytes


def _loads(text: str):
    return json.loads(text, object_hook=lambda d: bytes.fromhex(d["__bytes__"]) if "__bytes__" in d else d)


def load_gateway(uid: str) -> dict | None:
    with engine.connect() as c:
        row = c.execute(select(gateways).where(gateways.c.user_id == uid)).mappings().first()
    if not row: return None
    _last[uid] = row["state"] + row["ledger"]
    return {"state": _loads(row["state"]), "ledger": _loads(row["ledger"])}


def _upsert(c, uid: str, vals: dict) -> None:
    """One atomic statement: no UPDATE-then-INSERT gap locks, so concurrent users cannot deadlock each other."""
    if engine.dialect.name == "mysql":
        c.execute(mysql_insert(gateways).values(user_id=uid, **vals).on_duplicate_key_update(**vals))
    elif engine.dialect.name == "postgresql":
        c.execute(pg_insert(gateways).values(user_id=uid, **vals).on_conflict_do_update(index_elements=["user_id"], set_=vals))
    else:
        c.execute(sqlite_insert(gateways).values(user_id=uid, **vals).on_conflict_do_update(index_elements=["user_id"], set_=vals))


def save_gateway(uid: str, gw) -> None:
    state, ledger = gw.snapshot()
    s, l = _dumps(state), _dumps(ledger)
    if _last.get(uid) == s + l: return
    vals = {"state": s, "ledger": l, "updated": time.time()}
    for attempt in range(3):
        try:
            with engine.begin() as c:
                _upsert(c, uid, vals)
            break
        except OperationalError as e:                       # MySQL 1213 deadlock / 1205 lock wait: safe to retry
            if attempt == 2 or not any(code in str(e) for code in ("1213", "1205")): raise
            time.sleep(0.05 * (attempt + 1))
    _last[uid] = s + l
