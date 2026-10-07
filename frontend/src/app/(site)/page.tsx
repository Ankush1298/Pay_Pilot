import Link from "next/link";
import { Counter } from "@/components/Counter";
import { Hero } from "@/components/Hero";
import { Reveal } from "@/components/Reveal";

const features = [
  ["Passkey-only accounts", "No password and no seed phrase. Your device's biometric unlocks a key that never leaves it.", "M12 2a5 5 0 0 0-5 5v3H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-1V7a5 5 0 0 0-5-5zm-3 5a3 3 0 0 1 6 0v3H9V7z"],
  ["Policy engine outside the AI", "Merchant, payout address, amount, device and intent are checked by code the AI cannot edit or talk around.", "M12 2l9 4v6c0 5-3.8 8.8-9 10-5.2-1.2-9-5-9-10V6l9-4z"],
  ["Intent digests", "A SHA-256 digest of the exact transaction is the passkey challenge. Change anything and the signature stops matching.", "M4 4h16v4H4zM4 10h10v4H4zM4 16h16v4H4z"],
  ["Conversation memory, made safe", "The chat remembers your city and dates, and any value it filled in for you is shown and signed, never silently approved.", "M4 4h16v12H8l-4 4V4z"],
  ["New-device protection", "A fresh browser can sign in but is locked from spending until a trusted device approves it.", "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2zm5 18a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"],
  ["Security Lab", "Replay seven attacks (prompt injection, lookalike domains, velocity abuse) in a sandbox and watch the policy engine respond.", "M9 2h6v2l-1 1v5l5 9a2 2 0 0 1-1.7 3H6.700A2 2 0 0 1 5 19l5-9V5L9 4V2z"],
] as const;

const steps = [
  ["1", "You state a task", "“Find a hotel in Jaipur under ₹1,000.” The assistant searches merchants and compares options."],
  ["2", "Policy decides", "Each prepared payment becomes an intent. The engine answers Allow, Step-up or Block, and explains why."],
  ["3", "Passkey approves", "For step-ups your device signs the digest of that exact transaction. Only then does the ledger settle."],
] as const;

export default function Home() {
  return (
    <>
      <Hero />

      <section className="container stats" aria-label="At a glance">
        {[[7, "", "attack scenarios in the lab"], [120, " s", "passkey challenge lifetime"], [256, "-bit", "intent digest (SHA-256)"], [0, "", "passwords stored"]].map(([n, suf, label]) => (
          <Reveal key={String(label)} className="stat">
            <strong><Counter to={n as number} suffix={suf as string} /></strong>
            <span>{label}</span>
          </Reveal>
        ))}
      </section>

      <section id="features" className="container section">
        <Reveal><h2 className="section-title">Everything between the AI and your money</h2><p className="section-lead">Built so a compromised or confused assistant can propose anything, and still cannot spend without the right checks.</p></Reveal>
        <div className="feature-grid">
          {features.map(([t, d, icon], i) => (
            <Reveal key={t} delay={i * 0.05}>
              <article className="feature-card">
                <svg width="26" height="26" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d={icon} /></svg>
                <h3>{t}</h3><p>{d}</p>
              </article>
            </Reveal>
          ))}
        </div>
      </section>

      <section id="how" className="container section">
        <Reveal><h2 className="section-title">How it works</h2></Reveal>
        <ol className="steps">
          {steps.map(([n, t, d], i) => (
            <li key={n}><Reveal delay={i * 0.08}><div className="step"><span className="step-n">{n}</span><h3>{t}</h3><p>{d}</p></div></Reveal></li>
          ))}
        </ol>
      </section>

      <section className="container section">
        <Reveal>
          <div className="cta-band">
            <div><h2>See the gate in action</h2><p>Run the step-up flow in your browser, or create an account and approve a real passkey prompt.</p></div>
            <div className="cta-actions"><Link href="/demo" className="btn btn-primary btn-lg">Open the demo</Link><Link href="/security" className="btn btn-secondary btn-lg">Read how it&apos;s secured</Link></div>
          </div>
        </Reveal>
      </section>
    </>
  );
}
