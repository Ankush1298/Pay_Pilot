# PayPilot threat model

## Security boundary

**The AI proposes. The policy decides. The user approves sensitive actions.**

The AI can browse, compare and prepare a transaction, but it never receives the user's passkey, policy signer key, or relayer key.

## Threats and controls

| Threat | Control |
|---|---|
| Compromised AI redirects a booking | User intent binding + merchant payout verification + policy engine authorization (HMAC in the simulated ledger; policy signature in the reference contract) |
| AI changes hotel request into P2P transfer | Agent actions are type-bound to the active user intent; P2P is always step-up |
| Payment exceeds automatic ceiling | Policy returns STEP_UP; WebAuthn UV is required |
| Unknown/lookalike website | Merchant registry + lookalike detection + step-up/block |
| Payment destination changes after approval | Exact transaction hash binds merchant, amount, purpose, expiry and nonce |
| Replay | One-time intent status + nonce + expiry; the reference contract also tracks `used[intentHash]` |
| New device | New passkey login creates a pending device; payments are locked for the configured hold |
| Three suspicious attempts | Session termination and pending-device block; user signs in again with a passkey |
| Relayer compromise (reference contract) | Relayer has no policy key; the contract requires a policy signature and, for STEP_UP, a passkey signature |
| Policy-service compromise | **Out of scope / known weakness.** In the reference contract the policy signer alone can add a passkey or mark a merchant trusted, so a compromised policy service is not contained by the user's passkey. Needs a passkey-gated admin path before any real use |
| Passkey credential theft | WebAuthn user verification (UV) is required; credential private key remains with the platform authenticator |
| Password database breach | There are no passwords or password hashes |
| Recovery-code theft | There are no recovery codes; users register additional synced passkeys |

## WebAuthn verification

The browser uses discoverable WebAuthn credentials. The backend verifies the RP ID, origin, challenge, UP/UV flags, signature and sign counter. The reference contract (not deployed, on-chain WebAuthn path not yet covered by tests) is written to use a maintained `WebAuthn`/`P256` library rather than a hand-rolled verifier. The on-chain assertion reconstructs the WebAuthn message as `SHA256(authenticatorData || SHA256(clientDataJSON))` and requires `webauthn.get`, the expected base64url challenge, UP and UV.

## Important limitations

This is a hackathon prototype, not an audited wallet. The backend stores state in memory, the merchant sites are controlled demo fixtures, and the default ledger is simulated. The optional live testnet mode requires a deployed factory and funded accounts and is untested end to end. Never use real funds with this code.
