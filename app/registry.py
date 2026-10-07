"""Per-user Gateway registry with locking.

Keeps one Gateway instance per user_id in memory, protected by a per-user
threading.Lock so concurrent requests for the same user serialize correctly.

Backed by the database: loaded on a cache miss, written back after every request that changed it.
"""
from __future__ import annotations

import threading
from contextlib import contextmanager

from . import auth as AUTH
from . import config
from . import persist as PERSIST
from .gateway import Gateway

# ------------------------------------------------------------------ registry
_lock = threading.Lock()
_gateways: dict[str, Gateway] = {}        # user_id -> Gateway
_user_locks: dict[str, threading.Lock] = {}


def _get_lock(uid: str) -> threading.Lock:
    with _lock:
        if uid not in _user_locks:
            _user_locks[uid] = threading.Lock()
        return _user_locks[uid]


@contextmanager
def use(uid: str):
    """Context manager: acquire the per-user lock, yield the gateway, release."""
    ulock = _get_lock(uid)
    with ulock:
        if uid not in _gateways:
            user = AUTH.get_user_by_id(uid)
            username = user["username"] if user else uid
            # Per-user exec key is derived from a master key + uid (never stored).
            master = config.MASTER_KEY
            snap = PERSIST.load_gateway(uid)
            gw = Gateway(uid, username, master, snap and snap["state"], snap and snap["ledger"])
            # Wire revocation callbacks back into the auth layer.
            gw.on_revoke_session = AUTH.revoke_session
            gw.on_revoke_device = lambda did: None   # device revocation tracked in gw state
            _gateways[uid] = gw
        try:
            yield _gateways[uid]
        finally:
            if AUTH.get_user_by_id(uid): PERSIST.save_gateway(uid, _gateways[uid])     # this user only; skipped when nothing changed
            else: _gateways.pop(uid, None)                                            # account was deleted during the request


REG = type("_Reg", (), {"use": staticmethod(use)})()
