"""Ledger.

Default: a SIMULATED in-memory ledger (no network, no tokens, no deployment). Transaction hashes are
fake and have no explorer link. Optional live mode (INTENTLOCK_LEDGER=live) settles on Monad testnet
through the smart account in contracts/; it needs a deployed factory, a funded relayer and keys.
In live mode the relayer pays gas but never owns the user's smart-account funds.
"""
from __future__ import annotations
import base64, hashlib, json, os, time
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
from . import config
from .crypto import hmac_ok

class LedgerError(Exception): pass

class MockLedger:
    network = "simulated"
    def __init__(self, auth_key: bytes, user_addr: str, data=None, start_tmon=0.0):
        self._key, self.user_addr = auth_key, user_addr
        self.txs = data.get("txs", []) if data else []
    def to_dict(self): return {"txs": self.txs}
    def balance_tmon(self): return max(0.0, 1000.0 - sum(x.get("amount_tmon", 0) for x in self.txs))
    def faucet(self): raise LedgerError("Simulated ledger: there is nothing to fund")
    def initialize_wallet(self, *args, **kwargs): return self.user_addr
    def add_passkey(self, credential: dict): return True
    def set_policy(self, per_tx: int, daily: int, passkey_data: dict, intent_hash: str): return True
    def transfer(self, auth, digest, sender, to, amount_inr, memo="", allow_overdraft=False, intent_data=None, passkey_data=None):
        if not hmac_ok(self._key, digest, auth or ""): raise LedgerError("Invalid policy authorization")
        tx_hash = "0x" + hashlib.sha256(f"test:{digest}:{len(self.txs)}".encode()).hexdigest()
        tx = {"tx_hash": tx_hash, "block": 0, "digest": digest, "from": sender, "to": to,
              "amount_inr": amount_inr, "amount_tmon": amount_inr / config.INR_PER_MON,
              "memo": memo, "ts": time.time(), "network": self.network, "explorer_url": None, "simulated": True}
        self.txs.append(tx); return tx


def _load_deployments() -> dict:
    path = Path(config.DEPLOYMENTS_FILE)
    if not path.exists(): return {}
    try: return json.loads(path.read_text())
    except Exception: return {}

if config.SIMULATED:
    Ledger = MockLedger
else:
    try:
        from web3 import Web3
        from eth_account import Account
        from eth_account.messages import encode_defunct
    except ImportError as e:
        raise RuntimeError("Live Monad mode requires web3 and eth-account. Run: pip install -r requirements.txt") from e

    RPC_URL = config.RPC_URL
    EXPLORER_URL = config.EXPLORER_URL
    DEPLOYMENTS = _load_deployments()
    FACTORY = DEPLOYMENTS.get("IntentLockFactory")
    if not FACTORY or not config.RELAYER_KEY or not config.POLICY_SIGNER_KEY:
        raise RuntimeError("Live Monad mode is not configured. Set INTENTLOCK_RELAYER_KEY, INTENTLOCK_POLICY_SIGNER_KEY and deploy IntentLockFactory first.")

    w3 = Web3(Web3.HTTPProvider(RPC_URL))
    relayer = Account.from_key(config.RELAYER_KEY)
    policy_signer = Account.from_key(config.POLICY_SIGNER_KEY)
    RELAYER_ADDRESS = relayer.address
    POLICY_SIGNER_ADDRESS = policy_signer.address
    FACTORY_ABI = [
        {"inputs":[{"name":"x","type":"uint256"},{"name":"y","type":"uint256"}],"name":"predictAddress","outputs":[{"name":"","type":"address"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"keyId","type":"bytes32"},{"name":"x","type":"uint256"},{"name":"y","type":"uint256"},{"name":"policySigner","type":"address"},{"name":"perTxLimit","type":"uint256"},{"name":"dailyLimit","type":"uint256"},{"name":"trustedMerchants","type":"address[]"}],"name":"createWallet","outputs":[{"name":"wallet","type":"address"}],"stateMutability":"nonpayable","type":"function"},
    ]
    WALLET_ABI = [
        {"inputs":[{"components":[{"name":"merchant","type":"address"},{"name":"amount","type":"uint256"},{"name":"purposeHash","type":"bytes32"},{"name":"expiry","type":"uint64"},{"name":"nonce","type":"uint256"}],"name":"i","type":"tuple"},{"name":"policySig","type":"bytes"},{"name":"keyId","type":"bytes32"},{"components":[{"name":"authenticatorData","type":"bytes"},{"name":"clientDataJSON","type":"string"},{"name":"challengeIndex","type":"uint256"},{"name":"typeIndex","type":"uint256"},{"name":"r","type":"uint256"},{"name":"s","type":"uint256"}],"name":"auth","type":"tuple"}],"name":"execute","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"components":[{"name":"merchant","type":"address"},{"name":"amount","type":"uint256"},{"name":"purposeHash","type":"bytes32"},{"name":"expiry","type":"uint64"},{"name":"nonce","type":"uint256"}],"name":"i","type":"tuple"}],"name":"hashIntent","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"keyId","type":"bytes32"},{"name":"x","type":"uint256"},{"name":"y","type":"uint256"}],"name":"addPasskey","outputs":[],"stateMutability":"nonpayable","type":"function"},
        {"inputs":[{"name":"newPerTxLimit","type":"uint256"},{"name":"newDailyLimit","type":"uint256"}],"name":"hashPolicy","outputs":[{"name":"","type":"bytes32"}],"stateMutability":"view","type":"function"},
        {"inputs":[{"name":"newPerTxLimit","type":"uint256"},{"name":"newDailyLimit","type":"uint256"},{"name":"intentHash","type":"bytes32"},{"name":"keyId","type":"bytes32"},{"components":[{"name":"authenticatorData","type":"bytes"},{"name":"clientDataJSON","type":"string"},{"name":"challengeIndex","type":"uint256"},{"name":"typeIndex","type":"uint256"},{"name":"r","type":"uint256"},{"name":"s","type":"uint256"}],"name":"auth","type":"tuple"},{"name":"policySig","type":"bytes"}],"name":"setPolicy","outputs":[],"stateMutability":"nonpayable","type":"function"},
    ]

    def _checksum(a): return w3.to_checksum_address(a)
    def _sign_and_send(tx):
        tx.setdefault("from", RELAYER_ADDRESS)
        tx.setdefault("nonce", w3.eth.get_transaction_count(RELAYER_ADDRESS, "pending"))
        tx.setdefault("gasPrice", w3.eth.gas_price)
        if "gas" not in tx: tx["gas"] = int(w3.eth.estimate_gas(tx) * 1.2)
        signed = relayer.sign_transaction(tx)
        h = w3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
        if receipt.status != 1: raise LedgerError("Monad transaction reverted")
        return w3.to_hex(h), receipt

    class Ledger:
        network = "monad-testnet"
        def __init__(self, auth_key: bytes, user_addr: str | None, data=None, start_tmon=0.0):
            self._key, self.user_addr = auth_key, user_addr
            self.txs = data.get("txs", []) if data else []
        def to_dict(self): return {"txs": self.txs}
        def balance_tmon(self):
            return w3.eth.get_balance(self.user_addr) / 1e18 if self.user_addr else 0.0
        def faucet(self): raise LedgerError(f"Fund the smart account and relayer via {config.FAUCET_URL}")
        def initialize_wallet(self, credential: dict, per_tx=1500, daily=5000, trusted_merchants=None):
            if self.user_addr: return self.user_addr
            x = int(credential["pub_x"], 16); y = int(credential["pub_y"], 16)
            key_id = bytes.fromhex(credential["key_id"])
            factory = w3.eth.contract(address=_checksum(FACTORY), abi=FACTORY_ABI)
            trusted = [_checksum(x["pay_to"]) for x in (trusted_merchants or []) if x.get("pay_to") and w3.is_address(x["pay_to"])]
            predicted = factory.functions.predictAddress(x, y).call()
            if w3.eth.get_code(predicted) == b"":
                if w3.eth.get_balance(RELAYER_ADDRESS) == 0: raise LedgerError(f"Relayer {RELAYER_ADDRESS} needs testnet MON for gas")
                tx = factory.functions.createWallet(key_id, x, y, POLICY_SIGNER_ADDRESS, int(per_tx), int(daily), trusted).build_transaction({"from": RELAYER_ADDRESS})
                _sign_and_send(tx)
            self.user_addr = predicted
            return predicted
        def add_passkey(self, credential: dict):
            if not self.user_addr: raise LedgerError("Smart account is not deployed")
            x, y = int(credential["pub_x"], 16), int(credential["pub_y"], 16)
            key_id = bytes.fromhex(credential["key_id"])
            wallet = w3.eth.contract(address=_checksum(self.user_addr), abi=WALLET_ABI)
            tx = wallet.functions.addPasskey(key_id, x, y).build_transaction({"from": POLICY_SIGNER_ADDRESS})
            # Administrative key registration is a policy-service operation; user payments still use the relayer.
            signed = policy_signer.sign_transaction({**tx, "nonce": w3.eth.get_transaction_count(POLICY_SIGNER_ADDRESS, "pending"), "gasPrice": w3.eth.gas_price, "gas": int(w3.eth.estimate_gas(tx) * 1.2)})
            h = w3.eth.send_raw_transaction(signed.raw_transaction)
            receipt = w3.eth.wait_for_transaction_receipt(h, timeout=120)
            if receipt.status != 1: raise LedgerError("Passkey registration transaction reverted")
            return w3.to_hex(h)

        def set_policy(self, per_tx: int, daily: int, passkey_data: dict, intent_hash: str):
            if not self.user_addr: raise LedgerError("Smart account is not deployed")
            if not passkey_data: raise LedgerError("Policy changes require passkey verification")
            raw_sig = base64.urlsafe_b64decode(passkey_data["signature"] + "=" * (-len(passkey_data["signature"]) % 4))
            r, s = decode_dss_signature(raw_sig)
            auth_bytes = base64.urlsafe_b64decode(passkey_data["authenticatorData"] + "=" * (-len(passkey_data["authenticatorData"]) % 4))
            client_json = base64.urlsafe_b64decode(passkey_data["clientDataJSON"] + "=" * (-len(passkey_data["clientDataJSON"]) % 4)).decode()
            cidx = client_json.find('"challenge":"'); tidx = client_json.find('"type":"webauthn.get"')
            if cidx < 0 or tidx < 0: raise LedgerError("Invalid WebAuthn client data")
            auth_tuple = (auth_bytes, client_json, cidx, tidx, r, s)
            key_id = bytes.fromhex(passkey_data["key_id"])
            wallet = w3.eth.contract(address=_checksum(self.user_addr), abi=WALLET_ABI)
            h = wallet.functions.hashPolicy(int(per_tx), int(daily)).call()
            policy_sig = policy_signer.sign_message(encode_defunct(primitive=h)).signature
            tx = wallet.functions.setPolicy(int(per_tx), int(daily), bytes.fromhex(intent_hash), key_id, auth_tuple, policy_sig).build_transaction({"from": RELAYER_ADDRESS})
            tx_hash, _ = _sign_and_send(tx)
            return tx_hash

        def transfer(self, auth, digest, sender, to, amount_inr, memo="", allow_overdraft=False, intent_data=None, passkey_data=None):
            if not hmac_ok(self._key, digest, auth or ""): raise LedgerError("Ledger rejected transfer: invalid policy authorization")
            if not self.user_addr: raise LedgerError("Smart account is not deployed")
            if not w3.is_address(to): raise LedgerError("Invalid merchant address")
            amount_wei = int(round((amount_inr / config.INR_PER_MON) * 1e18))
            if not allow_overdraft and self.balance_tmon() < amount_wei / 1e18: raise LedgerError(f"Insufficient MON. Fund {self.user_addr} via {config.FAUCET_URL}")
            if w3.eth.get_balance(RELAYER_ADDRESS) == 0: raise LedgerError(f"Relayer {RELAYER_ADDRESS} needs MON for gas")
            if not intent_data: raise LedgerError("Missing exact intent data")
            purpose_hash = w3.keccak(text=intent_data["purpose"])
            expiry = int(intent_data["expiry"]); nonce = int(intent_data["nonce"], 16)
            intent_tuple = (_checksum(to), amount_wei, purpose_hash, expiry, nonce)
            wallet = w3.eth.contract(address=_checksum(self.user_addr), abi=WALLET_ABI)
            intent_hash = wallet.functions.hashIntent(intent_tuple).call()
            policy_sig = policy_signer.sign_message(encode_defunct(primitive=intent_hash)).signature
            auth_tuple = (b"", "", 0, 0, 0, 0)
            if passkey_data:
                raw_sig = base64.urlsafe_b64decode(passkey_data["signature"] + "=" * (-len(passkey_data["signature"]) % 4))
                if not raw_sig or raw_sig[0] != 0x30: raise LedgerError("Passkey signature is not DER encoded")
                r, s = decode_dss_signature(raw_sig)
                auth_bytes = base64.urlsafe_b64decode(passkey_data["authenticatorData"] + "=" * (-len(passkey_data["authenticatorData"]) % 4))
                client_json = base64.urlsafe_b64decode(passkey_data["clientDataJSON"] + "=" * (-len(passkey_data["clientDataJSON"]) % 4)).decode()
                cidx = client_json.find('"challenge":"')
                tidx = client_json.find('"type":"webauthn.get"')
                if cidx < 0 or tidx < 0: raise LedgerError("Passkey clientDataJSON missing WebAuthn challenge/type")
                auth_tuple = (auth_bytes, client_json, cidx, tidx, r, s)
                key_id = bytes.fromhex(passkey_data.get("key_id") or hashlib.sha256(passkey_data["id"].encode()).hexdigest())
            else:
                key_id = bytes(32)
            tx = wallet.functions.execute(intent_tuple, policy_sig, key_id, auth_tuple).build_transaction({"from": RELAYER_ADDRESS})
            tx_hash, receipt = _sign_and_send(tx)
            out = {"tx_hash": tx_hash, "block": receipt.blockNumber, "digest": digest, "from": sender, "to": to,
                   "amount_inr": amount_inr, "amount_tmon": amount_wei / 1e18, "memo": memo, "ts": time.time(),
                   "network": self.network, "explorer_url": f"{EXPLORER_URL}/tx/{tx_hash}"}
            self.txs.append(out); return out
