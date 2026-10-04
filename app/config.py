"""IntentLock configuration."""
from __future__ import annotations
import os
ORIGINS = ["http://localhost:3000", "http://localhost:8000", "http://127.0.0.1:3000", "http://127.0.0.1:8000"]
MASTER_KEY = bytes.fromhex(os.getenv("INTENTLOCK_MASTER_KEY", "a1b2c3d4e5f601020304050607080900" * 2))
SESSION_COOKIE = "il_sess"
DEVICE_COOKIE = "il_dev"
SESSION_TTL = 7 * 86400
RP_ID = os.getenv("INTENTLOCK_RP_ID", "localhost")
RP_NAME = "IntentLock"
# Ledger mode. "simulated" (default): in-memory ledger, no network, no tokens, no deployment.
# "live": optional Monad testnet settlement (needs a deployed factory, funded relayer and keys).
LEDGER_MODE = os.getenv("INTENTLOCK_LEDGER", "simulated").lower()
TEST_MODE = os.getenv("INTENTLOCK_TEST_MODE", "0") == "1"
SIMULATED = TEST_MODE or LEDGER_MODE != "live"
RPC_URL = os.getenv("MONAD_TESTNET_RPC", "https://testnet-rpc.monad.xyz")
FAUCET_URL = "https://faucet.monad.xyz"
EXPLORER_URL = os.getenv("MONAD_EXPLORER_URL", "https://testnet.monadvision.com")
INR_PER_MON = float(os.getenv("INTENTLOCK_INR_PER_MON", "100"))
RELAYER_KEY = os.getenv("INTENTLOCK_RELAYER_KEY", "")
POLICY_SIGNER_KEY = os.getenv("INTENTLOCK_POLICY_SIGNER_KEY", "")
DEPLOYMENTS_FILE = os.getenv("INTENTLOCK_DEPLOYMENTS", "deployments.json")
