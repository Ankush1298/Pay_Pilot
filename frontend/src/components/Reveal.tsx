"use client";

import { m } from "framer-motion";

/** Scroll-reveal: transform + opacity only. Reduced-motion users get the opacity fade (MotionConfig). */
export function Reveal({ children, delay = 0, className }: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <m.div className={className} initial={{ opacity: 0, y: 24 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true, margin: "-60px" }} transition={{ duration: 0.5, delay, ease: [0.22, 1, 0.36, 1] }}>
      {children}
    </m.div>
  );
}
