"use client";

import { m } from "framer-motion";

/** Page transition: opacity + a small translate, re-run on every navigation. */
export default function Template({ children }: { children: React.ReactNode }) {
  return (
    <m.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.28, ease: "easeOut" }}>
      {children}
    </m.div>
  );
}
