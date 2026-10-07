"use client";

import { m } from "framer-motion";

const ticks = Array.from({ length: 60 }, (_, i) => i);

/** The hero "vault dial": two counter-rotating rings, a pulsing core and a check. Animates transform/opacity only. */
export function VaultDial({ size = 360 }: { size?: number }) {
  return (
    <svg viewBox="0 0 360 360" width={size} height={size} role="img" aria-label="A vault dial with a passkey check at its centre" className="vault-dial">
      <defs>
        <radialGradient id="vg" cx="50%" cy="50%" r="50%"><stop offset="0%" stopColor="var(--accent)" stopOpacity="0.35" /><stop offset="100%" stopColor="var(--accent)" stopOpacity="0" /></radialGradient>
      </defs>
      <circle cx="180" cy="180" r="176" fill="url(#vg)" />
      <m.g style={{ transformOrigin: "180px 180px" }} animate={{ rotate: 360 }} transition={{ duration: 90, ease: "linear", repeat: Infinity }}>
        <circle cx="180" cy="180" r="160" fill="none" stroke="var(--border-strong)" strokeWidth="1.5" />
        {ticks.map((i) => (
          <line key={i} x1="180" y1="20" x2="180" y2={i % 5 === 0 ? 40 : 30} stroke={i % 15 === 0 ? "var(--accent)" : "var(--border-strong)"} strokeWidth={i % 5 === 0 ? 2.5 : 1.5} transform={`rotate(${i * 6} 180 180)`} />
        ))}
      </m.g>
      <m.g style={{ transformOrigin: "180px 180px" }} animate={{ rotate: -360 }} transition={{ duration: 60, ease: "linear", repeat: Infinity }}>
        <circle cx="180" cy="180" r="118" fill="none" stroke="var(--accent)" strokeOpacity="0.55" strokeWidth="2" strokeDasharray="4 10" />
        {[0, 120, 240].map((a) => (<circle key={a} cx="180" cy="62" r="7" fill="var(--accent)" transform={`rotate(${a} 180 180)`} />))}
      </m.g>
      <circle cx="180" cy="180" r="84" fill="var(--bg-card)" stroke="var(--border-strong)" strokeWidth="2" />
      <m.circle cx="180" cy="180" r="84" fill="none" stroke="var(--accent)" strokeWidth="2" style={{ transformOrigin: "180px 180px" }} animate={{ scale: [1, 1.18], opacity: [0.7, 0] }} transition={{ duration: 2.4, repeat: Infinity, ease: "easeOut" }} />
      <m.path d="M138 182l30 30 56-62" fill="none" stroke="var(--accent)" strokeWidth="14" strokeLinecap="round" strokeLinejoin="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 1.1, delay: 0.5, ease: "easeInOut" }} />
    </svg>
  );
}
