"""PayPilot configuration."""
from __future__ import annotations
import os
import logging
import secrets

logging.basicConfig(level=os.getenv("PAYPILOT_LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("paypilot")
# Origins the browser UI may call from (CSRF allowlist and WebAuthn origin allowlist). Extend with PAYPILOT_ORIGINS=a,b
ORIGINS = [
    "http://localhost:3000", "http://localhost:8000", "http://localhost:8001",
    "http://127.0.0.1:3000", "http://127.0.0.1:8000", "http://127.0.0.1:8001",
]
ORIGINS += [o.strip().rstrip("/") for o in os.getenv("PAYPILOT_ORIGINS", "").split(",") if o.strip()]
# Never ship a key in source. State is in memory, so a per-process random key loses nothing; set the env var
# (64 hex chars) to keep ledger authorizations valid across restarts once state is persisted.
if os.getenv("PAYPILOT_MASTER_KEY"):
    MASTER_KEY = bytes.fromhex(os.environ["PAYPILOT_MASTER_KEY"])
else:
    MASTER_KEY = secrets.token_bytes(32)
    log.warning("PAYPILOT_MASTER_KEY not set: using a random per-process key")
DB_PATH = os.getenv("PAYPILOT_DB", "paypilot.db")      # SQLite file, only used when no database URL is set; ":memory:" for tests
# MySQL in real use: mysql+pymysql://user:password@host:3306/paypilot?charset=utf8mb4
DATABASE_URL = os.getenv("PAYPILOT_DATABASE_URL") or ("sqlite://" if DB_PATH == ":memory:" else f"sqlite:///{DB_PATH}")
SESSION_COOKIE = "il_sess"
DEVICE_COOKIE = "il_dev"
SESSION_TTL = 7 * 86400
COOKIE_MAX_AGE = 365 * 86400      # device-recognition cookie; the server still expires the session after SESSION_TTL
RP_ID = os.getenv("PAYPILOT_RP_ID", "localhost")
RP_NAME = "PayPilot"
# Ledger mode. "simulated" (default): in-memory ledger, no network, no tokens, no deployment.
# "live": optional Monad testnet settlement (needs a deployed factory, funded relayer and keys).
LEDGER_MODE = os.getenv("PAYPILOT_LEDGER", "simulated").lower()
TEST_MODE = os.getenv("PAYPILOT_TEST_MODE", "0") == "1"
SIMULATED = TEST_MODE or LEDGER_MODE != "live"
RPC_URL = os.getenv("MONAD_TESTNET_RPC", "https://testnet-rpc.monad.xyz")
FAUCET_URL = "https://faucet.monad.xyz"
EXPLORER_URL = os.getenv("MONAD_EXPLORER_URL", "https://testnet.monadvision.com")
INR_PER_MON = float(os.getenv("PAYPILOT_INR_PER_MON", "100"))
RELAYER_KEY = os.getenv("PAYPILOT_RELAYER_KEY", "")
POLICY_SIGNER_KEY = os.getenv("PAYPILOT_POLICY_SIGNER_KEY", "")
DEPLOYMENTS_FILE = os.getenv("PAYPILOT_DEPLOYMENTS", "deployments.json")

# Global per-IP ceiling on /api requests per minute (per-endpoint limits for login, chat and payments are stricter).
RATE_LIMIT_PER_MIN = int(os.getenv("PAYPILOT_RATE_LIMIT_PER_MIN", "240"))
