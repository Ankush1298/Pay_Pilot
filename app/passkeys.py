"""Minimal WebAuthn (passkey) helpers.

This implements just what IntentLock needs:
  - Registration: options + verify (CBOR-free subset that browsers support)
  - Authentication (assertion): options + verify

The verification is intentionally strict:
  - rpIdHash checked
  - origin checked
  - flags: UP must be set; UV is required for registrations
  - sign_count monotonicity checked
  - credential public key stored as raw COSE EC2 P-256 bytes

We avoid third-party WebAuthn libraries so the demo runs with the base
`cryptography` package already in requirements.txt.
"""
from __future__ import annotations

import base64
import hashlib
import json
import struct
import time
import secrets

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature

from . import config


class PasskeyError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code, self.message = code, message


# ------------------------------------------------------------------ utilities
def b64u(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def resolve_origin(origin: str) -> str:
    """Normalise origin to scheme://host[:port], stripping trailing slashes."""
    return origin.rstrip("/")


def new_challenge(st, purpose: str, ttl: int = 120) -> str:
    """Store a new challenge in state and return its b64url value."""
    raw = base64.urlsafe_b64encode(secrets.token_bytes(32)).rstrip(b"=").decode()
    st.challenges[raw] = {"purpose": purpose, "exp": time.time() + ttl}
    return raw


# ------------------------------------------------------------------ registration
def registration_options(st, user_id: str, username: str, origin: str) -> dict:
    challenge = new_challenge(st, "register")
    rp_id = _rp_id(origin)
    return {
        "challenge": challenge,
        "rp": {"id": rp_id, "name": config.RP_NAME},
        "user": {"id": b64u(user_id.encode()), "name": username, "displayName": username},
        "pubKeyCredParams": [{"type": "public-key", "alg": -7}],  # ES256
        "authenticatorSelection": {"userVerification": "required", "residentKey": "required"},
        "timeout": 120_000,
        "attestation": "none",
    }


def verify_registration(st, device_id: str, origin: str, payload: dict, name: str) -> dict:
    """Verify a navigator.credentials.create() response and store the credential."""
    cd = payload.get("response", {})
    client_data_raw = cd.get("clientDataJSON", "")
    attestation_raw = cd.get("attestationObject", "")
    cred_id = payload.get("id", "")

    client_data, challenge = _parse_client_data(client_data_raw, "webauthn.create", resolve_origin(origin))
    c = st.challenges.pop(challenge, None)
    if not c or c.get("purpose") != "register" or c["exp"] < time.time():
        raise PasskeyError("bad_challenge", "Challenge expired or not found")

    auth_data = _parse_attestation_object(attestation_raw)
    _check_rp_id(auth_data, origin)
    _check_flags(auth_data, require_uv=True)

    pub_key_bytes = _extract_cose_key(auth_data)
    sign_count = _auth_data_sign_count(auth_data)

    cred = {
        "id": cred_id, "device_id": device_id, "name": (name or "Passkey")[:40],
        "pub_key_bytes": pub_key_bytes,
        "pub_x": pub_key_bytes[:32].hex(), "pub_y": pub_key_bytes[32:].hex(),
        "key_id": hashlib.sha256(cred_id.encode()).hexdigest(),
        "sign_count": sign_count, "created": time.time(),
    }
    st.credentials[cred_id] = cred
    return cred


# ------------------------------------------------------------------ assertion
def assertion_options(st, origin: str, allow_ids: list[str], challenge: str) -> dict:
    rp_id = _rp_id(origin)
    opts = {
        "challenge": challenge,
        "rpId": rp_id,
        "userVerification": "required",
        "timeout": 120_000,
    }
    if allow_ids:
        opts["allowCredentials"] = [{"type": "public-key", "id": cid} for cid in allow_ids]
    return opts


def verify_assertion(st, origin: str, payload: dict, expected_challenge: str, allowed_ids: list[str]):
    cd = payload.get("response", {})
    client_data_raw = cd.get("clientDataJSON", "")
    auth_data_raw = cd.get("authenticatorData", "")
    sig_raw = cd.get("signature", "")
    cred_id = payload.get("id", "")

    if cred_id not in allowed_ids:
        raise PasskeyError("wrong_credential", "Credential not registered on this device")

    cred = st.credentials.get(cred_id)
    if not cred:
        raise PasskeyError("unknown_credential", "Credential not found")

    client_data, challenge = _parse_client_data(client_data_raw, "webauthn.get", resolve_origin(origin))
    if challenge != expected_challenge:
        raise PasskeyError("bad_challenge", "Challenge mismatch")

    auth_data_bytes = _b64u_decode(auth_data_raw)
    _check_rp_id_bytes(auth_data_bytes, origin)
    _check_flags_bytes(auth_data_bytes, require_uv=True)

    sign_count = int.from_bytes(auth_data_bytes[33:37], "big")
    stored = cred.get("sign_count", 0)
    # sign_count=0 means authenticator doesn't track it; skip the check
    if sign_count > 0 and stored > 0 and sign_count <= stored:
        raise PasskeyError("sign_count_regression", "Sign counter did not advance (possible cloning)")

    # WebAuthn signs: authenticatorData || SHA256(clientDataJSON).
    # Keep this calculation in one place; the previous implementation
    # accidentally referenced a non-existent private helper (`_b64u`),
    # which caused a 500 after a valid passkey prompt.
    cd_bytes = _b64u_decode(client_data_raw) if isinstance(client_data_raw, str) else client_data_raw
    signed_data = auth_data_bytes + hashlib.sha256(cd_bytes).digest()

    _verify_p256_signature(cred["pub_key_bytes"], signed_data, sig_raw)

    if sign_count > 0:
        cred["sign_count"] = sign_count


# ------------------------------------------------------------------ internals
def _rp_id(origin: str) -> str:
    # Extract hostname from origin
    o = resolve_origin(origin)
    host = o.split("://", 1)[-1].split(":")[0].split("/")[0]
    return host or config.RP_ID


def _parse_client_data(raw: str, expected_type: str, expected_origin: str) -> tuple[dict, str]:
    try:
        data = json.loads(_b64u_decode(raw))
    except Exception:
        raise PasskeyError("bad_client_data", "Cannot parse clientDataJSON")
    if data.get("type") != expected_type:
        raise PasskeyError("bad_type", f"Expected {expected_type}, got {data.get('type')}")
    if resolve_origin(data.get("origin", "")) != expected_origin:
        raise PasskeyError("origin_mismatch",
                           f"Origin mismatch: expected '{expected_origin}', got '{data.get('origin')}'")
    return data, data.get("challenge", "")


def _parse_attestation_object(raw: str) -> bytes:
    """Extract authData from a 'none' attestation object (CBOR subset)."""
    try:
        data = _b64u_decode(raw)
        # Walk the CBOR map to find the "authData" key.
        # We only support the minimal subset produced by browsers for 'none' attestation.
        pos, auth_data = _cbor_find_auth_data(data)
        return auth_data
    except PasskeyError:
        raise
    except Exception as e:
        raise PasskeyError("bad_attestation", f"Cannot parse attestationObject: {e}")


def _cbor_find_auth_data(data: bytes) -> tuple[int, bytes]:
    """Minimal CBOR parser: find 'authData' key in a top-level map."""
    pos = 0

    def read_uint(p):
        b = data[p]
        ai = b & 0x1f
        if ai < 24:
            return p + 1, ai
        elif ai == 24:
            return p + 2, data[p + 1]
        elif ai == 25:
            return p + 3, struct.unpack_from(">H", data, p + 1)[0]
        elif ai == 26:
            return p + 5, struct.unpack_from(">I", data, p + 1)[0]
        raise PasskeyError("bad_cbor", "Unsupported CBOR integer")

    def read_item(p):
        b = data[p]
        major = (b & 0xe0) >> 5
        if major == 0:  # uint
            return read_uint(p)
        elif major == 2:  # bytes
            p2, n = read_uint(p)
            return p2 + n, data[p2:p2 + n]
        elif major == 3:  # text
            p2, n = read_uint(p)
            return p2 + n, data[p2:p2 + n].decode("utf-8")
        elif major == 4:  # array
            p2, n = read_uint(p)
            items = []
            for _ in range(n):
                p2, v = read_item(p2)
                items.append(v)
            return p2, items
        elif major == 5:  # map
            p2, n = read_uint(p)
            d = {}
            for _ in range(n):
                p2, k = read_item(p2)
                p2, v = read_item(p2)
                d[k] = v
            return p2, d
        raise PasskeyError("bad_cbor", f"Unsupported CBOR major type {major}")

    _, obj = read_item(pos)
    if not isinstance(obj, dict) or "authData" not in obj:
        raise PasskeyError("bad_attestation", "authData not found in attestation object")
    return pos, obj["authData"]


def _check_rp_id(auth_data: bytes, origin: str):
    _check_rp_id_bytes(auth_data, origin)


def _check_rp_id_bytes(auth_data: bytes, origin: str):
    expected_hash = hashlib.sha256(_rp_id(origin).encode()).digest()
    if auth_data[:32] != expected_hash:
        raise PasskeyError("rp_id_mismatch", "RP ID hash mismatch")


def _check_flags(auth_data: bytes, require_uv: bool = False):
    _check_flags_bytes(auth_data, require_uv)


def _check_flags_bytes(auth_data: bytes, require_uv: bool = False):
    flags = auth_data[32]
    if not (flags & 0x01):  # UP
        raise PasskeyError("up_not_set", "User presence flag not set")
    if require_uv and not (flags & 0x04):  # UV
        raise PasskeyError("uv_not_set", "User verification flag not set")


def _extract_cose_key(auth_data: bytes) -> bytes:
    """Extract the raw COSE key bytes for P-256 from authData."""
    # authData layout: rpIdHash(32) flags(1) signCount(4) aaguid(16) credIdLen(2) credId(var) coseKey(var)
    pos = 32 + 1 + 4 + 16
    cred_id_len = struct.unpack_from(">H", auth_data, pos)[0]
    pos += 2 + cred_id_len
    # The rest is the CBOR-encoded COSE key
    cose_bytes = auth_data[pos:]
    # Parse it to get x, y coordinates
    try:
        _, cose = _cbor_find_cose(cose_bytes)
        x = cose.get(-2) or cose.get(b"\xfe")
        y = cose.get(-3) or cose.get(b"\xfd")
        if not (isinstance(x, bytes) and isinstance(y, bytes) and len(x) == 32 and len(y) == 32):
            raise PasskeyError("bad_key", "Cannot extract P-256 coordinates from COSE key")
        return x + y  # 64 bytes: x || y
    except PasskeyError:
        raise
    except Exception as e:
        raise PasskeyError("bad_cose", f"Cannot parse COSE key: {e}")


def _cbor_find_cose(data: bytes) -> tuple[int, dict]:
    pos = 0

    def read_uint(p):
        b = data[p]
        ai = b & 0x1f
        if ai < 24:
            return p + 1, ai
        elif ai == 24:
            return p + 2, data[p + 1]
        elif ai == 25:
            return p + 3, struct.unpack_from(">H", data, p + 1)[0]
        elif ai == 26:
            return p + 5, struct.unpack_from(">I", data, p + 1)[0]
        raise PasskeyError("bad_cbor", "Unsupported CBOR integer")

    def read_neg_int(p):
        b = data[p]
        ai = b & 0x1f
        p2, n = read_uint(p)
        return p2, -(n + 1)

    def read_item(p):
        b = data[p]
        major = (b & 0xe0) >> 5
        if major == 0:
            return read_uint(p)
        elif major == 1:
            return read_neg_int(p)
        elif major == 2:
            p2, n = read_uint(p)
            return p2 + n, data[p2:p2 + n]
        elif major == 3:
            p2, n = read_uint(p)
            return p2 + n, data[p2:p2 + n].decode("utf-8")
        elif major == 5:
            p2, n = read_uint(p)
            d = {}
            for _ in range(n):
                p2, k = read_item(p2)
                p2, v = read_item(p2)
                d[k] = v
            return p2, d
        raise PasskeyError("bad_cbor", f"Unsupported major type {major}")

    p, obj = read_item(pos)
    return p, obj


def _auth_data_sign_count(auth_data: bytes) -> int:
    return struct.unpack_from(">I", auth_data, 33)[0]


def _verify_p256_signature(pub_key_bytes: bytes, signed_data: bytes, sig_raw: str):
    """Verify an ES256 signature. sig_raw is base64url-encoded DER or raw r||s."""
    try:
        sig_bytes = _b64u_decode(sig_raw)
        x = int.from_bytes(pub_key_bytes[:32], "big")
        y = int.from_bytes(pub_key_bytes[32:], "big")
        pub = ec.EllipticCurvePublicNumbers(x, y, ec.SECP256R1()).public_key()
        # Browsers produce DER-encoded signatures for WebAuthn.
        # If it starts with 0x30 it's DER; otherwise treat as raw r||s.
        if sig_bytes[0] == 0x30:
            der = sig_bytes
        elif len(sig_bytes) == 64:
            r = int.from_bytes(sig_bytes[:32], "big")
            s = int.from_bytes(sig_bytes[32:], "big")
            der = encode_dss_signature(r, s)
        else:
            raise PasskeyError("bad_sig", "Unexpected signature format")
        pub.verify(der, signed_data, ec.ECDSA(hashes.SHA256()))
    except PasskeyError:
        raise
    except Exception:
        raise PasskeyError("bad_signature", "Signature verification failed")
