"""Test helpers: a fake 'browser device' that signs exactly like WebCrypto does."""
import base64

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature


def _b64u(n: int) -> str:
    return base64.urlsafe_b64encode(n.to_bytes(32, "big")).rstrip(b"=").decode()


class Device:
    def __init__(self, client, name="Laptop"):
        self.key = ec.generate_private_key(ec.SECP256R1())
        nums = self.key.public_key().public_numbers()
        self.jwk = {"kty": "EC", "crv": "P-256", "x": _b64u(nums.x), "y": _b64u(nums.y)}
        r = client.post("/api/devices/login", json={"name": name, "public_jwk": self.jwk}).json()
        self.id, self.token, self.status = r["device"]["id"], r["token"], r["device"]["status"]
        self.c = client

    @property
    def h(self):
        return {"Authorization": f"Bearer {self.token}"}

    def sign(self, message: str) -> str:
        der = self.key.sign(message.encode(), ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der)
        return base64.b64encode(r.to_bytes(32, "big") + s.to_bytes(32, "big")).decode()

    def get(self, path):
        return self.c.get(path, headers=self.h)

    def post(self, path, json=None):
        return self.c.post(path, json=json or {}, headers=self.h)

    def state(self):
        return self.get("/api/state").json()

    def search(self, msg, mode="careful"):
        return self.post("/api/agent/chat", {"message": msg, "mode": mode}).json()

    def book(self, opt, mode="careful"):
        return self.post("/api/agent/prepare", {"option_id": opt["id"], "mode": mode}).json()

    def approve(self, intent):
        return self.post(f"/api/intents/{intent['id']}/approve", {"signature": self.sign(intent["digest"])})
