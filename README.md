# PayPilot

**The AI proposes. The policy decides. Your passkey approves.**

PayPilot is a security gateway for autonomous AI actions. The AI can search merchant sites, compare
prices and reviews, fill a booking and prepare payment, but it cannot redefine the user's intent or
authenticate as the user. Accounts are **passkey-only** (WebAuthn, ECDSA P-256): no password, no seed
phrase, no recovery codes.

This is a hackathon demo. It runs entirely on your machine: **no deployment, no wallet, no tokens.**
The ledger is simulated by default (see "What is real and what is simulated").

## Run it

Two terminals.

```bash
# Terminal 1: backend (FastAPI)
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt            # requirements-dev.txt adds pytest/ruff/mypy
python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# Terminal 2: frontend (Next.js)
cd frontend && npm install && npm run dev      # http://localhost:3000
```

`./run.sh` does both. Open <http://localhost:3000>. Use `localhost` (WebAuthn needs a secure context
and the relying-party ID defaults to `localhost`; override with `PAYPILOT_RP_ID`). You need a browser
and device that support passkeys (Touch ID, Windows Hello, Android, or a security key).

Tests: `pip install -r requirements-dev.txt && python -m pytest -q` (includes an end-to-end run with a software
passkey, `tests/virtual_authenticator.py`). Lint/types: `ruff check app tests && mypy app`; frontend: `npm run lint && npm run build`.

## What the demo shows

1. **Passkey-only account.** Registration creates a discoverable (resident) passkey (ES256 / P-256,
   user verification required). Login calls `navigator.credentials.get()` without `allowCredentials`
   and identifies the account from `userHandle`. More passkeys can be registered on the account,
   including synced ones (iCloud Keychain, Google Password Manager).
2. **Intent-bound actions.** "Book a hotel in Jaipur under ₹1,500" becomes a temporary intent. A later
   request for a different category, city, P2P transfer or a higher price is blocked.
3. **Broad discovery, narrow authority.** The agent can browse the demo merchants; payment is checked
   separately for domain, merchant identity, payout address, device, amount and risk.
4. **Risk-based approval.** A trusted merchant on a trusted device within the automatic ceiling runs
   without a prompt. Above the ceiling, for an unfamiliar merchant, P2P, cancellation or other sensitive
   actions, a **passkey assertion whose challenge is the digest of that exact transaction** is required.
5. **Compromised-agent defense.** The Security Lab lets the agent meet a prompt injection that tries to
   redirect payment; the policy engine blocks the payout-address mismatch.
6. **New-device protection.** The same passkey can sign in on another browser, but that browser is a
   pending device and cannot spend until a trusted device approves it (or blocks it).
7. **Booking lifecycle.** Cancellation, refund and modification go back through the same policy gate.

## How passkey approval works

1. Registration: `navigator.credentials.create` → server parses the attestation object, checks origin,
   RP ID hash and the UP/UV flags, and stores the raw P-256 public key (`app/passkeys.py`).
2. When policy returns `STEP_UP`, the intent gets a SHA-256 digest over type, merchant, payout address,
   amount, currency, purpose, payload, expiry, nonce and device. **That digest is the WebAuthn challenge.**
3. The authenticator signs `authenticatorData ‖ SHA-256(clientDataJSON)`.
4. The server checks challenge == digest, origin, RP ID hash, UP/UV flags, the sign counter and the P-256
   signature, re-evaluates policy, and only then settles.

Challenges are random (`secrets.token_bytes(32)`), single-use and expire after 120 s.

## What is real and what is simulated

| Piece | Status |
|---|---|
| Passkey registration, login, approval (WebAuthn / P-256) | **Real**, verified server-side |
| Policy engine, intent binding, devices, strikes, audit log | **Real** |
| Merchants, websites, prompt-injection fixtures, the agent's "intelligence" | **Simulated** (rule-based demo fixtures) |
| Ledger | **Simulated by default**: in-memory, fake transaction ids, no explorer links, no funds |
| Smart-account contract (`contracts/PayPilotWallet.sol`) | **Reference code, not deployed.** See below |

## Smart-account reference design (optional, not deployed)

`contracts/PayPilotWallet.sol` is a non-ERC-4337 smart account owned by P-256/WebAuthn public keys,
created by a CREATE2/Clones factory from the key's coordinates. The policy service signs every payment
(ECDSA); `STEP_UP` payments also need a WebAuthn assertion verified on-chain with a WebAuthn library
(P-256 via the native verifier at `0x100` where available, EIP-7951, with a Solidity fallback).

Status, honestly:
* It has **not** been deployed and is **not** used by the default demo.
* The Foundry tests currently cover address derivation only. The on-chain WebAuthn path is untested.
* The WebAuthn import path should be checked after installing dependencies. OpenZeppelin documents its
  `WebAuthn` library under `community-contracts`; if `@openzeppelin/contracts/.../WebAuthn.sol` does not
  exist in the version you install, change the import or use `base-org/webauthn-sol`.
* Known design limits: `createWallet` is permissionless and takes the policy signer and limits from the
  caller (a front-runner could create a wallet for someone else's key with their own policy signer), and
  `addPasskey` / `setTrustedMerchant` need only the policy signer. Both must be fixed before any real use.

### Optional: live Monad testnet mode

Not needed for the demo. If you want to try it: `PAYPILOT_LEDGER=live`, `pip install -r
requirements-live.txt`, install the contract dependencies with Foundry, deploy the factory, record the
addresses in `deployments.json`, and set `PAYPILOT_RELAYER_KEY` and `PAYPILOT_POLICY_SIGNER_KEY`
(see `.env.example`). Both keys' accounts need testnet MON for gas. Monad's testnet details are in the
official docs: <https://docs.monad.xyz/developer-essentials/testnets>. Live mode is untested end to end.

## Limitations

* State is in memory; restarting the server resets everything.
* Attestation is `none`: we verify the key and signatures, not the authenticator model.
* The OS passkey prompt cannot show transaction details; PayPilot's own dialog renders them from the
  server's record, and the signature binds to the same digest.
* The WebAuthn CBOR parser is a minimal subset for `none` attestation. Use a vetted library in production.
* Single relying party (`localhost` by default); rate limiting is in-process per IP.
* The master key has a development default unless `PAYPILOT_MASTER_KEY` is set.
* The injection scanner is a heuristic; the real defense is that policy ignores what the AI believes.
* Not audited. Do not use real funds.

## Project layout

- `app/passkeys.py`: WebAuthn registration and assertion verification.
- `app/auth.py`: passkey-only sessions and device cookies.
- `app/policy.py`: ALLOW / STEP_UP / BLOCK decisions.
- `app/gateway.py`: intent lifecycle, passkey approval, devices, bookings.
- `app/agent.py`: simulated agent; it can only submit intents.
- `app/ledger.py`: simulated ledger (default) and optional live Monad settlement.
- `app/merchants.py`, `app/lab.py`: demo merchants and Security Lab scenarios.
- `contracts/`: reference smart account, factory, deploy script, Foundry tests.
- `frontend/`: Next.js UI (`src/lib/passkeys.ts` runs the browser WebAuthn ceremonies).
- `THREAT_MODEL.md`: attacker model.
# Pay_Pilot
