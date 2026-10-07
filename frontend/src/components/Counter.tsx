"use client";

import { animate, useInView, useReducedMotion } from "framer-motion";
import { useEffect, useRef } from "react";

/** Counts up when scrolled into view. Writes straight to the DOM node, so it never re-renders React. */
export function Counter({ to, suffix = "", duration = 1.4 }: { to: number; suffix?: string; duration?: number }) {
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });
  const reduce = useReducedMotion();
  useEffect(() => {
    if (!inView || !ref.current) return;
    const el = ref.current;
    if (reduce) { el.textContent = `${to}${suffix}`; return; }
    const c = animate(0, to, { duration, ease: "easeOut", onUpdate: (v) => { el.textContent = `${Math.round(v)}${suffix}`; } });
    return () => c.stop();
  }, [inView, to, suffix, duration, reduce]);
  return <span ref={ref}>{`${to}${suffix}`}</span>;
}
