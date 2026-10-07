# Hosting PayPilot

Two pieces. The browser only ever talks to the frontend; Next.js proxies `/api`, `/merchant`
and `/merchants` to the backend, so cookies and WebAuthn stay same-origin.

## 1. Backend (needs an always-on host: Render, Railway, Fly.io)
Build from the root `Dockerfile`. Run **one instance** (state is in memory). Environment:

| Variable | Value |
|---|---|
| `PAYPILOT_RP_ID` | the frontend's host name, e.g. `paypilot.vercel.app` (no scheme) |
| `PAYPILOT_ORIGINS` | the frontend's origin, e.g. `https://paypilot.vercel.app` |
| `PAYPILOT_MASTER_KEY` | `openssl rand -hex 32` |
| `PAYPILOT_DATABASE_URL` | optional MySQL URL; without it a local SQLite file is used and is lost on redeploy |

## 2. Frontend (Vercel)
Import the repo, set **Root Directory** to `frontend`, and add:

| Variable | Value |
|---|---|
| `BACKEND_URL` | the backend's public URL, no trailing slash |
| `NEXT_PUBLIC_SITE_URL` | the frontend's public URL |

If you later attach a custom domain, update `PAYPILOT_RP_ID` / `PAYPILOT_ORIGINS`.
Passkeys are bound to the RP ID, so changing it invalidates registered passkeys.
