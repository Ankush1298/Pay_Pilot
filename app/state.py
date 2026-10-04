"""In-memory application state (swap for a database in production)."""
from __future__ import annotations

import copy
import time

DEFAULT_POLICY = {
    "per_tx_limit": 1500,          # auto-approve up to this amount (INR)
    "daily_limit": 5000,           # rolling 24h cumulative auto-spend
    "absolute_cap": 25000,         # never allowed, even with strong auth
    "allowed_types": ["hotel", "movie", "restaurant", "flight", "shopping"],
    "approved_merchants": [],      # unverified registry domains the user trusts
    "velocity_max": 3,             # max auto payments per window
    "velocity_window_s": 600,
    "new_device_lock_hours": 24,
    "strike_limit": 3,
}


class State:
    def __init__(self, data: dict | None = None):
        if data:
            self._load(data)
        else:
            self._init_fresh()

    def _init_fresh(self):
        self.clock_offset = 0.0
        self.created = time.time()
        self.policy = copy.deepcopy(DEFAULT_POLICY)
        self.devices: dict[str, dict] = {}
        self.sessions: dict[str, dict] = {}
        self.credentials: dict[str, dict] = {}   # passkey credentials
        self.challenges: dict[str, dict] = {}    # challenge -> {purpose, exp}
        self.intents: dict[str, dict] = {}
        self.bookings: dict[str, dict] = {}
        self.connections: dict[str, dict] = {}   # domain -> connection info
        self.audit: list[dict] = []
        self.alerts: list[dict] = [
        ]
        self.nonces: set[str] = set()
        self.executions: list[dict] = []
        self.wallet_address = None
        self.active_user_intent = None
        self.onboarding_open = True

    def _load(self, data: dict):
        self._init_fresh()
        for k, v in data.items():
            if k == "nonces":
                self.nonces = set(v)
            else:
                setattr(self, k, v)

    def to_dict(self) -> dict:
        d = {}
        for k in ("clock_offset", "created", "policy", "devices", "sessions", "credentials",
                  "challenges", "intents", "bookings", "connections", "audit", "alerts",
                  "executions", "wallet_address", "active_user_intent", "onboarding_open"):
            d[k] = getattr(self, k)
        d["nonces"] = list(self.nonces)
        return d

    def now(self) -> float:
        return time.time() + self.clock_offset

    def log(self, kind: str, message: str, level: str = "info", **extra):
        self.audit.append({"ts": self.now(), "kind": kind, "message": message, "level": level, **extra})

    def alert(self, level: str, message: str, device_id: str | None = None):
        self.alerts.append({"ts": self.now(), "level": level, "message": message, "device_id": device_id})
        self.log("alert", message, level)

    def spent_since(self, t: float) -> float:
        return sum(e["amount"] for e in self.executions if e["ts"] >= t)

    def count_since(self, t: float) -> int:
        return sum(1 for e in self.executions if e["ts"] >= t)
