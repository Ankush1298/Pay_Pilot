"use client";

import { m } from "framer-motion";

/** Drawn-in approve (check) / deny (cross) mark with a ring burst. Used on the step-up screen and in the demo. */
export function VerdictMark({ verdict, size = 96 }: { verdict: "approved" | "denied"; size?: number }) {
  const ok = verdict === "approved";
  const color = ok ? "var(--success)" : "var(--danger)";
  return (
    <m.svg viewBox="0 0 96 96" width={size} height={size} role="img" aria-label={ok ? "Approved" : "Denied"} initial={{ scale: 0.6, opacity: 0 }} animate={ok ? { scale: [0.6, 1.08, 1], opacity: 1 } : { scale: 1, opacity: 1, x: [0, -6, 6, -4, 4, 0] }} transition={{ duration: 0.5 }}>
      <m.circle cx="48" cy="48" r="40" fill="none" stroke={color} strokeOpacity="0.9" strokeWidth="4" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.45 }} />
      <m.circle cx="48" cy="48" r="40" fill="none" stroke={color} strokeWidth="2" style={{ transformOrigin: "48px 48px" }} initial={{ scale: 1, opacity: 0.6 }} animate={{ scale: 1.5, opacity: 0 }} transition={{ duration: 0.8, delay: 0.3 }} />
      {ok ? (
        <m.path d="M28 50l14 14 27-30" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.4, delay: 0.35 }} />
      ) : (
        <>
          <m.path d="M32 32l32 32" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.25, delay: 0.3 }} />
          <m.path d="M64 32L32 64" fill="none" stroke={color} strokeWidth="6" strokeLinecap="round" initial={{ pathLength: 0 }} animate={{ pathLength: 1 }} transition={{ duration: 0.25, delay: 0.5 }} />
        </>
      )}
    </m.svg>
  );
}
