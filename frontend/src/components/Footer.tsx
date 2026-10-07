"use client";

import Link from "next/link";
import { useState } from "react";
import { footerColumns, site } from "@/config/site";
import { Logo } from "./Logo";

const Icon = ({ d }: { d: string }) => (<svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true"><path d={d} /></svg>);
const GH = "M12 .5a11.5 11.5 0 0 0-3.6 22.4c.6.1.8-.3.8-.6v-2c-3.2.7-3.9-1.5-3.9-1.5-.5-1.3-1.3-1.7-1.3-1.7-1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.7 1.3 3.3 1 .1-.7.4-1.3.7-1.6-2.6-.3-5.3-1.3-5.3-5.7 0-1.3.5-2.3 1.2-3.1-.1-.3-.5-1.5.1-3.1 0 0 1-.3 3.2 1.2a11 11 0 0 1 5.8 0c2.2-1.5 3.2-1.2 3.2-1.2.6 1.6.2 2.8.1 3.1.8.8 1.2 1.8 1.2 3.1 0 4.4-2.7 5.4-5.3 5.7.4.4.8 1.1.8 2.2v3.2c0 .3.2.7.8.6A11.5 11.5 0 0 0 12 .5z";
const X = "M18.2 2h3.3l-7.2 8.3L22.8 22h-6.6l-5.2-6.8L5 22H1.7l7.7-8.8L1.2 2h6.8l4.7 6.2L18.2 2zm-1.2 18h1.8L7 3.9H5.1L17 20z";
const LI = "M4.9 3.5a2.4 2.4 0 1 1 0 4.8 2.4 2.4 0 0 1 0-4.8zM2.8 9.6h4.2V22H2.8V9.6zm6.8 0h4v1.7h.1c.6-1.1 2-2 4-2 4.3 0 5.1 2.8 5.1 6.5V22h-4.2v-5.4c0-1.3 0-3-1.8-3s-2.1 1.4-2.1 2.9V22H9.6V9.6z";

export function Footer() {
  const [email, setEmail] = useState("");
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const subscribe = (e: React.FormEvent) => {
    e.preventDefault();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setMsg({ ok: false, text: "Please enter a valid email address." });
    // UI only: there is no mailing-list backend yet, so nothing is stored or sent.
    setMsg({ ok: true, text: "Thanks! This form isn't connected to a mailing list yet, so nothing was saved." });
    setEmail("");
  };

  return (
    <footer className="site-footer">
      <div className="container footer-grid">
        <div className="footer-brand">
          <Logo />
          <p>{site.tagline}</p>
          <address>
            <a href={`mailto:${site.contact.email}`}>{site.contact.email}</a>
            <a href={`tel:${site.contact.phone.replace(/\s/g, "")}`}>{site.contact.phone}</a>
            <span>{site.contact.address}</span>
          </address>
          <div className="socials">
            <a href={site.social.github} aria-label="PayPilot on GitHub" target="_blank" rel="noopener noreferrer"><Icon d={GH} /></a>
            <a href={site.social.twitter} aria-label="PayPilot on X (Twitter)" target="_blank" rel="noopener noreferrer"><Icon d={X} /></a>
            <a href={site.social.linkedin} aria-label="PayPilot on LinkedIn" target="_blank" rel="noopener noreferrer"><Icon d={LI} /></a>
          </div>
        </div>
        {footerColumns.map((col) => (
          <nav key={col.title} aria-label={col.title} className="footer-col">
            <h2>{col.title}</h2>
            <ul>{col.links.map(([label, href]) => (<li key={label}><Link href={href}>{label}</Link></li>))}</ul>
          </nav>
        ))}
        <form className="footer-news" onSubmit={subscribe} noValidate>
          <h2>Get updates</h2>
          <label htmlFor="news-email" className="sr-only">Email address</label>
          <div className="news-row">
            <input id="news-email" className="input" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" aria-describedby="news-msg" />
            <button className="btn btn-primary" type="submit">Subscribe</button>
          </div>
          <p id="news-msg" role="status" className={msg ? (msg.ok ? "form-ok" : "form-err") : "form-hint"}>{msg?.text ?? "Product news only. No spam."}</p>
        </form>
      </div>
      <div className="container footer-bottom">
        <span>© {new Date().getFullYear()} {site.name}. Hackathon prototype, not an audited payment product.</span>
        <button type="button" className="link-btn" onClick={() => window.dispatchEvent(new Event("pp:cookie-settings"))}>Cookie settings</button>
      </div>
    </footer>
  );
}
