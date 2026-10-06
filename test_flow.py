import requests
import json

base_url = "http://127.0.0.1:8000"

# Register options
res = requests.post(f"{base_url}/api/auth/register/options", json={"username": "testuser"})
print("Options:", res.status_code)

# We can't easily mock WebAuthn clientDataJSON without a real browser or proper mock.
