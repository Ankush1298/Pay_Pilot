"""Live attack probe: starts a real server on MySQL (database paypilot_test, simulated ledger) and runs 19 checks.

Run by hand: create the paypilot_test database first, then `python tests/live_security_probe.py`. Not collected by pytest.
"""
import os, subprocess, sys, time, threading, httpx
sys.path.insert(0, "/Volumes/Ankush/Pay-Pilot")
from tests.virtual_authenticator import VirtualAuthenticator
PORT = 8005; BASE = f"http://127.0.0.1:{PORT}"; H = {"origin": "http://localhost:3000"}
url = open("/Volumes/Ankush/Pay-Pilot/.env").read().split("PAYPILOT_DATABASE_URL=")[1].split("\n")[0].replace("/paypilot?", "/paypilot_test?")
env = {**os.environ, "PAYPILOT_DATABASE_URL": url, "PAYPILOT_LEDGER": "simulated", "PAYPILOT_RATE_LIMIT_PER_MIN": "100000"}
for k in ("PAYPILOT_TEST_MODE",): env.pop(k, None)
srv = subprocess.Popen([".venv/bin/python","-m","uvicorn","app.main:app","--port",str(PORT)], env=env, stdout=subprocess.DEVNULL, stderr=open("/tmp/sec_probe.log","w"))
for _ in range(40):
    try: httpx.get(BASE+"/api/health", timeout=1); break
    except Exception: time.sleep(0.5)
results = []
def check(name, ok, detail=""): results.append((ok, name, detail)); print(("PASS" if ok else "FAIL"), "-", name, detail, flush=True)
def register(name, ip=None):
    c = httpx.Client(base_url=BASE, timeout=60, headers={"x-forwarded-for": ip} if ip else None); a = VirtualAuthenticator()
    o = c.post("/api/auth/register/options", json={"username": name}, headers=H).json()
    r = c.post("/api/auth/register/verify", json={"credential": a.create(o)}, headers=H)
    return c, a, r
try:
    c, a, r = register("probe-a"); cb, ab, rb = register("probe-b")
    check("registration works on MySQL", r.status_code == 200 and rb.status_code == 200)
    # 1 headers
    h = c.get("/api/auth/session", headers=H).headers
    check("security headers", h.get("x-content-type-options")=="nosniff" and h.get("x-frame-options")=="DENY" and h.get("cache-control")=="no-store", str({k:h.get(k) for k in ("x-content-type-options","x-frame-options","cache-control","referrer-policy")}))
    # 2 cookie flags
    sc = r.headers.get("set-cookie","").lower()
    check("session cookie HttpOnly + SameSite=lax", "httponly" in sc and "samesite=lax" in sc, sc[:90])
    # 3 CSRF
    x = httpx.Client(base_url=BASE, cookies=c.cookies)
    check("cross-origin POST rejected", x.post("/api/auth/logout", headers={"origin":"https://evil.example"}).status_code == 403)
    check("sec-fetch-site cross-site rejected", x.post("/api/auth/logout", headers={**H, "sec-fetch-site":"cross-site"}).status_code == 403)
    # 4 unauthenticated
    anon = httpx.Client(base_url=BASE)
    codes = {p: anon.get(p).status_code for p in ("/api/state","/api/chat/conversations","/api/auth/sessions")}
    check("protected endpoints need login", all(v == 401 for v in codes.values()), str(codes))
    # 5/13 IDOR
    chat = c.post("/api/agent/chat", json={"message":"find a hotel in Jaipur tomorrow"}, headers=H).json(); cid = chat["conversation_id"]
    check("other user cannot read my conversation", cb.get(f"/api/chat/conversations/{cid}").status_code == 404 and c.get(f"/api/chat/conversations/{cid}").status_code == 200)
    d = cb.delete(f"/api/chat/conversations/{cid}", headers=H)
    check("other user cannot delete my conversation", c.get(f"/api/chat/conversations/{cid}").status_code == 200, f"delete->{d.status_code} (conversation still there)")
    cp = cb.patch(f"/api/chat/conversations/{cid}/context", json={"context": {"city": "Goa"}}, headers=H)
    check("other user cannot edit my conversation context", cp.status_code == 404 and c.get(f"/api/chat/conversations/{cid}").json()["context"].get("city") == "Jaipur", f"patch->{cp.status_code}")
    opt = chat["options"][-1]["id"]
    it = c.post("/api/agent/prepare", json={"option_id": opt}, headers=H).json()
    p1 = cb.post("/api/agent/prepare", json={"option_id": opt}, headers=H)
    p2 = cb.post(f"/api/intents/{it['id']}/approval-options", headers=H)
    p3 = cb.post(f"/api/intents/{it['id']}/approve", json={"credential": {}}, headers=H)
    check("other user cannot use my option/intent", p1.status_code == 404 and p2.status_code in (404, 409) and p3.status_code == 404, f"prepare->{p1.status_code} approval-options->{p2.status_code} approve->{p3.status_code} intent={it.get('status')}")
    # 6 SQL injection
    ri = httpx.Client(base_url=BASE).post("/api/auth/register/options", json={"username": "x'; DROP TABLE users;--"}, headers=H)
    check("SQL-injection username handled", ri.status_code == 200)
    r1 = c.post("/api/agent/chat", json={"message":"hotel in ' OR 1=1 --", "conversation_id": "cv_x' OR '1'='1"}, headers=H)
    check("SQL-injection conversation id harmless", r1.status_code in (404, 422), str(r1.status_code))
    check("users table still intact", c.get("/api/auth/session", headers=H).json().get("authenticated") is True)
    # 8 oversized
    big = c.post("/api/agent/chat", json={"message":"a"*2_000_000}, headers=H)
    check("oversized message rejected", big.status_code in (413,422), str(big.status_code))
    # 11 tokens hashed
    raw = c.cookies.get("il_sess").split(":")[0]
    out = subprocess.run(["mysql","-u","root","paypilot_test","-N","-e",f"select count(*) from sessions where token_hash='{raw}'"],capture_output=True,text=True).stdout.strip()
    check("raw session token not stored in DB", out == "0", f"rows with raw token={out}")
    # 7 logout + replay
    cookies = dict(c.cookies); c.post("/api/auth/logout", headers=H)
    check("revoked session cannot be replayed", httpx.Client(base_url=BASE, cookies=cookies).get("/api/state").status_code == 401)
    # 9 login brute force rate limit
    env_limit = httpx.Client(base_url=BASE); codes=[]
    for _ in range(40): codes.append(env_limit.post("/api/auth/login/options", headers=H).status_code)
    check("login endpoint rate limited", 429 in codes, f"first 429 at request #{codes.index(429)+1 if 429 in codes else None}")
    # 10 XSS username stored verbatim as data (React escapes on render)
    cx, ax, rx = register("<img src=x onerror=alert(1)>")
    check("XSS-looking name stored as plain data", cx.get("/api/auth/session", headers=H).json().get("username","").startswith("<img"))
    # 14 concurrency: 40 users at once
    errs = []; done = []
    def worker(i):
        try:
            _, _, rr = register(f"conc-{i}-{int(time.time())}", ip=f"203.0.113.{i+1}")
            (done if rr.status_code == 200 else errs).append(rr.status_code)
        except Exception as e: errs.append(repr(e)[:80])
    ts = [threading.Thread(target=worker, args=(i,)) for i in range(40)]
    t0 = time.time(); [t.start() for t in ts]; [t.join() for t in ts]
    n = subprocess.run(["mysql","-u","root","paypilot_test","-N","-e","select count(*) from users u join gateways g on g.user_id=u.id where u.username like 'conc-%'"],capture_output=True,text=True).stdout.strip()
    check("40 simultaneous registrations all saved", len(done) == 40 and not errs and n == "40", f"ok={len(done)} errors={errs[:2]} rows={n} in {time.time()-t0:.1f}s")
finally:
    srv.terminate()
bad = [r for r in results if not r[0]]
print(f"\n{len(results)-len(bad)}/{len(results)} checks passed"); sys.exit(1 if bad else 0)
