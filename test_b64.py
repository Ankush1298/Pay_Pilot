import base64
def _b64u_encode(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")

def _b64u_decode(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (4 - len(s) % 4))

uid = "u_1234567890abcdef"
b64 = _b64u_encode(uid.encode())
print("b64:", b64)
decoded = _b64u_decode(b64).decode()
print("decoded:", decoded)
print("matches:", uid == decoded)
