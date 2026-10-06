import type { Metadata } from "next";
import { Legal } from "@/components/Prose";
import { site } from "@/config/site";

export const metadata: Metadata = { title: "Privacy Policy", description: "What PayPilot stores, why, and what never leaves your device." };

export default function Page() {
  return (
    <Legal title="Privacy Policy">
      <h2>What never leaves your device</h2>
      <p>Your fingerprint, face or device PIN is checked by your own device. {site.name} never receives it. Your passkey&apos;s private key stays on your device (or in your platform&apos;s passkey sync, such as iCloud Keychain or Google Password Manager). We only receive a public key and signed proofs.</p>
      <h2>What we store</h2>
      <ul>
        <li><strong>Account:</strong> the display name you choose and a random account ID. There are no passwords, password hashes or recovery codes.</li>
        <li><strong>Passkeys:</strong> credential ID, public key, a sign counter and a label.</li>
        <li><strong>Devices and sessions:</strong> a device name derived from your browser, its user-agent string, IP address, first-seen time and trust status; session records and a device-recognition token.</li>
        <li><strong>Activity:</strong> payment intents (merchant, destination address, amount, purpose, status), bookings, ledger entries, an audit log of policy decisions, and security alerts.</li>
        <li><strong>Chat:</strong> your messages to the booking assistant, its replies, and the small context it keeps per conversation (such as city, dates, budget). Chats are stored in a database on the server so they survive a page refresh and re-login. You can delete a conversation.</li>
        <li><strong>Settings:</strong> your spending limits and allowed transaction types.</li>
      </ul>
      <p>In this version most account data is held in the server&apos;s memory and is lost when the server restarts. Chat history is stored in a database file on the server.</p>
      <h2>Why</h2>
      <p>To sign you in, enforce your security policy, show your history, and keep the assistant&apos;s conversation coherent. We do not sell data, and we do not use it for advertising.</p>
      <h2>Third parties</h2>
      <p>This demo uses simulated merchants and a simulated ledger by default. No analytics or advertising trackers are included. Fonts are served from this site. If the optional live testnet mode is enabled, transaction details are written to a public blockchain, which cannot be erased.</p>
      <h2>Cookies and local storage</h2>
      <p>See the <a href="/cookies">Cookie Policy</a>.</p>
      <h2>Retention and your choices</h2>
      <p>You can end sessions and block devices in the app, and delete chat conversations. To ask for access to or deletion of your data, contact us at <a href={`mailto:${site.contact.email}`}>{site.contact.email}</a>. <em>[Retention periods and your legal rights depend on your jurisdiction; to be completed with legal advice.]</em></p>
      <h2>Security</h2>
      <p>Sessions use HttpOnly cookies, requests are origin-checked, and sensitive actions need a passkey. This is a prototype and has not been independently audited, so please do not use real funds or sensitive data.</p>
      <h2>Contact</h2>
      <p>{site.contact.email}, {site.contact.address}</p>
    </Legal>
  );
}
