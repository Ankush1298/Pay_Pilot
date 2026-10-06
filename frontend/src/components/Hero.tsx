"use client";

import Link from "next/link";
import { m } from "framer-motion";
import { VaultDial } from "./VaultDial";

const words = ["The", "AI", "proposes.", "The", "policy", "decides.", "Your", "passkey", "approves."];

export function Hero() {
  return (
    <section className="hero container">
      <div className="hero-copy">
        <m.p className="eyebrow" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}>Security gateway for AI agents that spend money</m.p>
        <h1 className="hero-title" aria-label={words.join(" ")}>
          {words.map((w, i) => (
            <m.span key={i} aria-hidden="true" className={`hero-word ${i >= 6 ? "grad" : ""}`} initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 + i * 0.07, duration: 0.45, ease: "easeOut" }}>{w}{" "}</m.span>
          ))}
        </h1>
        <m.p className="hero-sub" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.9 }}>
          Let an assistant search, compare and prepare bookings, without ever handing it your money. Every payment is checked by a policy engine
          outside the AI, and anything sensitive needs a passkey signature over the exact transaction.
        </m.p>
        <m.div className="hero-cta" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 1.05 }}>
          <m.span whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}><Link href="/register" className="btn btn-primary btn-lg">Create account</Link></m.span>
          <m.span whileHover={{ y: -2 }} whileTap={{ scale: 0.97 }}><Link href="/demo" className="btn btn-secondary btn-lg">Try the demo</Link></m.span>
        </m.div>
      </div>
      <m.div className="hero-art" initial={{ opacity: 0, scale: 0.92 }} animate={{ opacity: 1, scale: 1 }} transition={{ duration: 0.8, delay: 0.2 }}>
        <VaultDial />
      </m.div>
    </section>
  );
}
