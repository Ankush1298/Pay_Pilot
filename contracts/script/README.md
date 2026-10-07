# Optional: Monad testnet deployment (not needed for the demo)

The default demo uses a simulated ledger and does not deploy anything. This is only for trying live mode.

Install Foundry, then (if your Foundry version rejects `--no-commit`, drop that flag; and check that the WebAuthn import in `PayPilotWallet.sol` resolves, see the main README) from the repository root:

```bash
forge install OpenZeppelin/openzeppelin-contracts@v5.7.0 --no-commit
forge install foundry-rs/forge-std --no-commit
export DEPLOYER_PRIVATE_KEY=0x...
forge script contracts/script/Deploy.s.sol:Deploy --rpc-url https://testnet-rpc.monad.xyz --broadcast
```

Copy the emitted `PayPilotFactory` and implementation addresses into `deployments.json`.
Do **not** invent addresses. The checked-in file intentionally has `deployed: false` until a real deployment is made.

The factory derives each account address deterministically from the P-256 public key coordinates using CREATE2/Clones.
