"""A software WebAuthn authenticator (ES256, 'none' attestation) for end-to-end tests."""
import base64, hashlib, json, os, struct

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

ORIGIN = "http://localhost:3000"
RP_ID = "localhost"


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def unb64u(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _hdr(major: int, n: int) -> bytes:
    if n < 24:
        return bytes([major << 5 | n])
    if n < 256:
        return bytes([major << 5 | 24, n])
    return bytes([major << 5 | 25]) + struct.pack(">H", n)


def _cbor(o) -> bytes:
    if isinstance(o, int):
        return _hdr(0, o) if o >= 0 else _hdr(1, -1 - o)
    if isinstance(o, bytes):
        return _hdr(2, len(o)) + o
    if isinstance(o, str):
        return _hdr(3, len(o.encode())) + o.encode()
    if isinstance(o, dict):
        return _hdr(5, len(o)) + b"".join(_cbor(k) + _cbor(v) for k, v in o.items())
    raise TypeError(o)


class VirtualAuthenticator:
    def __init__(self, origin=ORIGIN, rp_id=RP_ID):
        self.key = ec.generate_private_key(ec.SECP256R1())
        self.cred_id = os.urandom(16)
        self.origin, self.rp_id, self.count = origin, rp_id, 0
        self.user_handle = b""

    @property
    def id(self) -> str:
        return b64u(self.cred_id)

    def _client_data(self, typ: str, challenge: str, origin=None) -> bytes:
        return json.dumps({"type": typ, "challenge": challenge, "origin": origin or self.origin}, separators=(",", ":")).encode()   # compact like real browsers

    def create(self, opts: dict, *, flags=0x45, origin=None, cred_id=None) -> dict:
        self.user_handle = unb64u(opts["user"]["id"])
        n = self.key.public_key().public_numbers()
        cose = _cbor({1: 2, 3: -7, -1: 1, -2: n.x.to_bytes(32, "big"), -3: n.y.to_bytes(32, "big")})
        cid = cred_id if cred_id is not None else self.cred_id
        auth = (hashlib.sha256(self.rp_id.encode()).digest() + bytes([flags | 0x40]) + struct.pack(">I", 0)
                + bytes(16) + struct.pack(">H", len(cid)) + cid + cose)
        att = _cbor({"fmt": "none", "attStmt": {}, "authData": auth})
        cd = self._client_data("webauthn.create", opts["challenge"], origin)
        return {"id": self.id, "type": "public-key",
                "response": {"clientDataJSON": b64u(cd), "attestationObject": b64u(att)}}

    def get(self, opts: dict, *, flags=0x05, origin=None, count=None, challenge=None) -> dict:
        self.count = count if count is not None else self.count + 1
        auth = hashlib.sha256(self.rp_id.encode()).digest() + bytes([flags]) + struct.pack(">I", self.count)
        cd = self._client_data("webauthn.get", challenge or opts["challenge"], origin)
        sig = self.key.sign(auth + hashlib.sha256(cd).digest(), ec.ECDSA(hashes.SHA256()))
        return {"id": self.id, "type": "public-key",
                "response": {"clientDataJSON": b64u(cd), "authenticatorData": b64u(auth),
                             "signature": b64u(sig), "userHandle": b64u(self.user_handle)}}
