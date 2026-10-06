import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/Prose";
import { Reveal } from "@/components/Reveal";

export const metadata: Metadata = { title: "Security", description: "Passkeys, intent digests, the policy engine and the ledger, explained in plain language." };

const blocks = [
  ["Passkeys", "A passkey is a key pair made by your device. The private half never leaves it and is unlocked by your fingerprint, face or PIN. PayPilot only keeps the public half, so there is no password to steal or phish, and nothing for a database leak to expose. When you approve something, your device signs a challenge, and we check the signature, the website origin, that you were present and verified, and that the signature counter moved forward."],
  ["Intent digests", "Every payment the AI prepares becomes an intent: type, merchant, destination address, amount, currency, purpose, details, expiry, a one-time nonce and the device. We hash all of it with SHA-256. That digest is the challenge your passkey signs, so your approval is bound to exactly that transaction. If anything changes by even one character, the signature no longer matches. Values the chat filled in from earlier in the conversation (like the city) are inside the digest too, and are listed on the approval screen."],
  ["The policy engine", "A separate piece of code decides Allow, Step-up or Block. It checks the device, the merchant and its registered payout address, lookalike domains, the amount against your limits, how many payments happened recently, and whether the request matches what you originally asked for. The AI cannot change these rules, and anything it reports about itself can only raise the risk, never lower it."],
  ["The ledger", "Money only moves through the ledger, and the ledger only accepts a transfer that carries an authorization the policy engine minted for that exact digest. Each authorization works once, so replaying an approved request does nothing. By default the ledger is simulated and no real funds are involved."],
] as const;

const threats = [
  ["Prompt injection redirects a payment", "The payout address is checked against the merchant's registered address. A mismatch is blocked outright."],
  ["A lookalike website", "Domains that imitate a registered merchant are blocked; unknown merchants always need your passkey."],
  ["Someone replays an approval", "Intents are single-use with a nonce and expiry, and the ledger refuses a digest it has already settled."],
  ["A new device signs in", "It is locked from spending until a trusted device approves it."],
  ["The AI asks for something you never asked for", "Requests must match your original task (type, city, budget), or they are blocked."],
] as const;

export default function Security() {
  return (
    <Page eyebrow="Security" title="How PayPilot keeps AI payments safe" lead="No jargon version. For the full attacker model, see the threat model in the repository.">
      <div className="stack">
        {blocks.map(([t, d], i) => (<Reveal key={t} delay={i * 0.04}><section className="card"><h2>{t}</h2><p>{d}</p></section></Reveal>))}
      </div>
      <h2 id="threats" className="section-title" style={{ marginTop: "3rem" }}>Attacks we defend against</h2>
      <ul className="threat-list">{threats.map(([a, b]) => (<li key={a}><strong>{a}</strong><span>{b}</span></li>))}</ul>
      <div className="legal-warn" role="note">
        <strong>Honest limits.</strong> This is a hackathon prototype and has not been independently audited. We hold no security certifications. Account data is held in memory and
        resets on restart, and the on-chain contract is reference code that is not deployed. Do not use real funds.
      </div>
      <p style={{ marginTop: "2rem" }}><Link href="/demo" className="btn btn-primary">See the decisions in the demo</Link></p>
    </Page>
  );
}
