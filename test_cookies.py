import requests

session = requests.Session()
proxy_url = "http://localhost:3000"

# Note: since we can't easily do webauthn in python, we can't fully register.
# But we can inspect the headers returned by a mock login or register if we bypass webauthn in a patch.
