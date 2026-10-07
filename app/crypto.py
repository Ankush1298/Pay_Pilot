"""Cryptographic helpers for PayPilot.

* Intents are hashed over a canonical JSON encoding, so a signature binds
  merchant + amount + purpose + expiry + nonce (the *exact* transaction).
* User approvals are ECDSA P-256 signatures made by a passkey. In the demo
  the key lives in the browser (WebCrypto); in production it would be a
  WebAuthn / passkey credential held in a secure element.
* The policy engine authorizes the ledger with an HMAC that only it can make.
  The AI agent never sees this key.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(obj) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def _b64url_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def verify_p256(public_jwk: dict, message: bytes, signature_b64: str) -> bool:
    """Verify a WebCrypto ECDSA/SHA-256 signature (raw r||s, base64)."""
    try:
        x = int.from_bytes(_b64url_decode(public_jwk["x"]), "big")
        y = int.from_bytes(_b64url_decode(public_jwk["y"]), "big")
        pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        raw = base64.b64decode(signature_b64)
        if len(raw) != 64:
            return False
        der = encode_dss_signature(int.from_bytes(raw[:32], "big"), int.from_bytes(raw[32:], "big"))
        pub.verify(der, message, ec.ECDSA(hashes.SHA256()))
        return True
    except (InvalidSignature, KeyError, ValueError, TypeError):
        return False


def hmac_tag(key: bytes, message: str) -> str:
    return hmac.new(key, message.encode(), hashlib.sha256).hexdigest()


def hmac_ok(key: bytes, message: str, tag: str) -> bool:
    return hmac.compare_digest(hmac_tag(key, message), tag or "")
