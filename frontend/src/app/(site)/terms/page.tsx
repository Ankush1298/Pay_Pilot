import type { Metadata } from "next";
import { Legal } from "@/components/Prose";
import { site } from "@/config/site";

export const metadata: Metadata = { title: "Terms & Conditions", description: "The terms for using the PayPilot prototype." };

export default function Page() {
  return (
    <Legal title="Terms & Conditions">
      <h2>1. What this is</h2>
      <p>{site.name} is a prototype of a security gateway for AI agents. By default it runs with simulated merchants and a simulated ledger. No real money moves and no real bookings are made.</p>
      <h2>2. No financial or professional advice</h2>
      <p>Nothing here is financial, legal or security advice. {site.name} is not a bank, payment institution or wallet provider.</p>
      <h2>3. Your account</h2>
      <p>Your account is protected by your passkey. You are responsible for the devices that hold it. If you lose a device, sign in from another one that has your passkey and block the lost device in Settings. There are no recovery codes.</p>
      <h2>4. Acceptable use</h2>
      <p>Do not attack, overload or reverse-engineer the service in ways that harm others, do not try to access other users&apos; data, and do not use the service for unlawful purposes. Testing the Security Lab is welcome.</p>
      <h2>5. No warranty</h2>
      <p>The service is provided &quot;as is&quot;, without warranties of any kind. It is not audited. Do not use real funds or sensitive personal data. To the extent the law allows, we are not liable for losses arising from its use.</p>
      <h2>6. Changes and termination</h2>
      <p>We may change the service or these terms, or suspend access, at any time. Because state may be reset when the server restarts, accounts and history are not guaranteed to persist.</p>
      <h2>7. Governing law</h2>
      <p><em>[To be completed with legal advice: governing law, jurisdiction and dispute resolution.]</em></p>
      <h2>8. Contact</h2>
      <p><a href={`mailto:${site.contact.email}`}>{site.contact.email}</a></p>
    </Legal>
  );
}
