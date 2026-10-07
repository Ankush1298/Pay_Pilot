"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { AnimatePresence, m } from "framer-motion";
import { nav } from "@/config/site";
import { useAuth } from "./AuthContext";
import { Logo } from "./Logo";
import { ThemeToggle } from "./ThemeToggle";

export function Navbar() {
  const { user, loading } = useAuth();
  const pathname = usePathname();
  const [open, setOpen] = useState(false);

  useEffect(() => { setOpen(false); }, [pathname]);
  useEffect(() => {
    const esc = (e: KeyboardEvent) => { if (e.key === "Escape") setOpen(false); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, []);

  const links = (
    <>
      {nav.map((n) => (<Link key={n.href} href={n.href} className="nav-link">{n.label}</Link>))}
    </>
  );
  const cta = loading ? null : user ? (
    <Link href="/dashboard" className="btn btn-primary btn-sm">Dashboard</Link>
  ) : (
    <>
      <Link href="/login" className="btn btn-ghost btn-sm">Log in</Link>
      <Link href="/register" className="btn btn-primary btn-sm">Register</Link>
    </>
  );

  return (
    <header className="site-nav">
      <div className="container nav-inner">
        <Logo />
        <nav aria-label="Primary" className="nav-links">{links}</nav>
        <div className="nav-actions">
          <ThemeToggle />
          <div className="nav-cta">{cta}</div>
          <button type="button" className="icon-btn nav-burger" aria-expanded={open} aria-controls="mobile-menu" aria-label={open ? "Close menu" : "Open menu"} onClick={() => setOpen((o) => !o)}>
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">{open ? <path d="M6 6l12 12M18 6L6 18" /> : <path d="M4 7h16M4 12h16M4 17h16" />}</svg>
          </button>
        </div>
      </div>
      <AnimatePresence>
        {open && (
          <m.div id="mobile-menu" className="mobile-menu" initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -8 }} transition={{ duration: 0.18 }}>
            <nav aria-label="Mobile" className="container">{links}<div className="mobile-cta">{cta}</div></nav>
          </m.div>
        )}
      </AnimatePresence>
    </header>
  );
}
