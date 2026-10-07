"use client";

import { useState } from "react";
import { AnimatePresence, m } from "framer-motion";
import { VerdictMark } from "./VerdictMark";

type Scenario = { id: string; label: string; title: string; merchant: string; amount: string; to: string; verdict: "ALLOW" | "STEP_UP" | "BLOCK"; reasons: string[] };

const scenarios: Scenario[] = [
  { id: "auto", label: "₹800 hotel", title: "Pink City Residency · 1 night", merchant: "grandstay.mock (verified)", amount: "₹800", to: "0x4f1a…9c2e", verdict: "ALLOW", reasons: ["Trusted device", "Verified merchant, payout address matches", "Below your automatic ceiling"] },
  { id: "step", label: "₹2,400 hotel", title: "Maharaja Suites · 1 night", merchant: "royalpalace.mock (verified)", amount: "₹2,400", to: "0x91be…03d7", verdict: "STEP_UP", reasons: ["Above your ₹1,500 automatic ceiling", "A passkey signature over this exact transaction is required"] },
  { id: "evil", label: "Hijacked agent", title: "Amber Fort View · 1 night", merchant: "lucky-stays.example (unverified)", amount: "₹499", to: "0xdead…beef", verdict: "BLOCK", reasons: ["Payout address does not match the merchant's registered address", "The page contained hidden instructions aimed at the AI"] },
];

type Phase = "idle" | "signing" | "approved" | "denied";

/** A client-only simulation of the real flow. No passkey is involved here, and the page says so. */
export function StepUpDemo() {
  const [sid, setSid] = useState("step");
  const [phase, setPhase] = useState<Phase>("idle");
  const s = scenarios.find((x) => x.id === sid)!;
  const choose = (id: string) => { setSid(id); setPhase(scenarios.find((x) => x.id === id)!.verdict === "ALLOW" ? "approved" : "idle"); };
  const sign = () => { setPhase("signing"); setTimeout(() => setPhase("approved"), 1400); };

  return (
    <div className="demo-card">
      <div className="seg" role="tablist" aria-label="Scenario">
        {scenarios.map((x) => (
          <button key={x.id} role="tab" aria-selected={sid === x.id} className={sid === x.id ? "on" : ""} onClick={() => choose(x.id)}>{x.label}</button>
        ))}
      </div>
      <div className="demo-intent">
        <div className="demo-row"><span>Agent asks to pay</span><strong>{s.amount}</strong></div>
        <div className="demo-row"><span>For</span><strong>{s.title}</strong></div>
        <div className="demo-row"><span>Merchant</span><strong>{s.merchant}</strong></div>
        <div className="demo-row"><span>Destination</span><strong className="mono">{s.to}</strong></div>
        <div className="demo-verdict">
          <span className={`badge ${s.verdict === "BLOCK" ? "badge-danger" : s.verdict === "STEP_UP" ? "badge-warn" : "badge-ok"}`}>{s.verdict.replace("_", "-")}</span>
          <ul>{s.reasons.map((r) => (<li key={r}>{r}</li>))}</ul>
        </div>
      </div>
      <div className="demo-stage" aria-live="polite">
        <AnimatePresence mode="wait">
          {s.verdict === "BLOCK" ? (
            <m.div key="blocked" className="demo-result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><VerdictMark verdict="denied" /><p>Blocked by the policy engine. You cannot approve this one, and neither can the AI.</p></m.div>
          ) : phase === "approved" ? (
            <m.div key="ok" className="demo-result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><VerdictMark verdict="approved" /><p>{s.verdict === "ALLOW" ? "Auto-approved within your policy. No prompt needed." : "Passkey verified. The ledger settled exactly what you saw."}</p></m.div>
          ) : phase === "denied" ? (
            <m.div key="no" className="demo-result" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}><VerdictMark verdict="denied" /><p>Denied. Nothing was charged.</p></m.div>
          ) : (
            <m.div key="act" className="demo-actions" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <button className="btn btn-ghost" onClick={() => setPhase("denied")} disabled={phase === "signing"}>Deny</button>
              <m.button className="btn btn-primary" onClick={sign} disabled={phase === "signing"} whileTap={{ scale: 0.97 }}>
                {phase === "signing" ? (<><span className="spinner" /> Waiting for your fingerprint…</>) : "Verify with passkey"}
              </m.button>
            </m.div>
          )}
        </AnimatePresence>
      </div>
      <p className="demo-note">Simulation: no real passkey or money is involved here. Register to try the real flow.</p>
    </div>
  );
}
