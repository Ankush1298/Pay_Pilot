# IntentLock frontend

Next.js frontend for the IntentLock hackathon prototype.

## Run

```bash
npm ci
npm run dev
```

Open `http://localhost:3000`.

The frontend proxies `/api/*` to the FastAPI server at `http://127.0.0.1:8000`.

Authentication is **passkey-only**. Registration creates a discoverable resident credential (`residentKey: required`) and login uses `navigator.credentials.get()` without `allowCredentials`; the returned WebAuthn `userHandle` identifies the account.

The app supports a live Monad testnet mode. For automated tests only, set `INTENTLOCK_TEST_MODE=1` to enable the mock ledger.
