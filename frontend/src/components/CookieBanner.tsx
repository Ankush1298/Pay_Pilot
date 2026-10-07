"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { CONSENT_KEY } from "./ThemeToggle";

type Consent = { preferences: boolean; ts: number };

export function CookieBanner() {
  const [consent, setConsent] = useState<Consent | null | undefined>(undefined); // undefined = not read yet
  const [manage, setManage] = useState(false);
  const [prefs, setPrefs] = useState(false);

  useEffect(() => {
    try { setConsent(JSON.parse(localStorage.getItem(CONSENT_KEY) || "null")); } catch { setConsent(null); }
    const reopen = () => { setManage(true); setConsent(null); };
    window.addEventListener("pp:cookie-settings", reopen);
    return () => window.removeEventListener("pp:cookie-settings", reopen);
  }, []);

  const save = (preferences: boolean) => {
    const c = { preferences, ts: Date.now() };
    try {
      localStorage.setItem(CONSENT_KEY, JSON.stringify(c));
      if (!preferences) localStorage.removeItem("pp_theme_v2");
      else localStorage.setItem("pp_theme_v2", document.documentElement.dataset.theme || "light");
    } catch { /* storage blocked: choice only lasts for this page view */ }
    setConsent(c); setManage(false);
  };

  if (consent !== null) return null;
  return (
    <section className="cookie-banner" role="region" aria-label="Cookie consent">
      <div className="cookie-body">
        <h2>Cookies &amp; storage</h2>
        <p>
          We use one essential cookie to keep you signed in. With your permission we also remember your theme choice in your browser.
          No analytics or advertising trackers. See the <Link href="/cookies">Cookie Policy</Link>.
        </p>
        {manage && (
          <div className="cookie-manage">
            <label className="switch-row"><input type="checkbox" checked disabled /> <span><strong>Essential</strong> · sign-in session and device recognition. Always on.</span></label>
            <label className="switch-row"><input type="checkbox" checked={prefs} onChange={(e) => setPrefs(e.target.checked)} /> <span><strong>Preferences</strong> · remember light/dark theme.</span></label>
          </div>
        )}
      </div>
      <div className="cookie-actions">
        {manage ? (
          <button className="btn btn-primary btn-sm" onClick={() => save(prefs)}>Save choices</button>
        ) : (
          <>
            <button className="btn btn-primary btn-sm" onClick={() => save(true)}>Accept</button>
            <button className="btn btn-secondary btn-sm" onClick={() => setManage(true)}>Manage</button>
          </>
        )}
      </div>
    </section>
  );
}
