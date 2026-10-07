import type { Metadata } from "next";
import { Legal } from "@/components/Prose";
import { CookieSettingsButton } from "@/components/CookieSettingsButton";

export const metadata: Metadata = { title: "Cookie Policy", description: "The cookies and browser storage PayPilot uses." };

export default function Page() {
  return (
    <Legal title="Cookie Policy">
      <p>We use the minimum needed to run the app. We do not use analytics, advertising or cross-site tracking cookies.</p>
      <div className="table-wrap"><table className="data-table">
        <thead><tr><th>Name</th><th>Type</th><th>Purpose</th><th>Lifetime</th></tr></thead>
        <tbody>
          <tr><td className="mono">il_sess</td><td>Essential cookie (HttpOnly, SameSite=Lax; Secure on HTTPS)</td><td>Keeps you signed in and lets us recognise a browser you have already trusted.</td><td>Up to 1 year; the sign-in session itself expires after 7 days on the server</td></tr>
          <tr><td className="mono">pp_consent</td><td>Local storage (essential)</td><td>Remembers your cookie choice.</td><td>Until you clear site data</td></tr>
          <tr><td className="mono">pp_theme_v2</td><td>Local storage (preference, only if you allow it)</td><td>Remembers light or dark mode.</td><td>Until you clear site data</td></tr>
        </tbody>
      </table></div>
      <h2>Your choices</h2>
      <p>Essential items cannot be switched off, because the app cannot work without them. You can allow or refuse preference storage at any time.</p>
      <p><CookieSettingsButton /></p>
      <p>You can also clear cookies and site data in your browser settings; you will be signed out.</p>
    </Legal>
  );
}
