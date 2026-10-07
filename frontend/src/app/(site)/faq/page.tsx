import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/Prose";

export const metadata: Metadata = { title: "FAQ", description: "Answers to common questions about PayPilot." };

const faqs: [string, React.ReactNode][] = [
  ["Do I need a password?", "No. Accounts are passkey-only. Your device unlocks a key with your fingerprint, face or PIN."],
  ["Does PayPilot get my fingerprint or face?", "No. Biometrics are checked on your device and never sent to us."],
  ["What if I lose my device?", "Sign in from another device that has your passkey (synced passkeys such as iCloud Keychain or Google Password Manager help), then block the lost device in Settings. There are no recovery codes."],
  ["Does the AI have access to my money?", "No. The AI can only propose. A policy engine decides, and sensitive payments need your passkey signature over the exact transaction."],
  ["Why did the chat ask me to confirm a cheap booking?", "When the assistant fills in a detail from earlier in the conversation (for example the city), that payment always needs your approval so you see exactly what it assumed."],
  ["Does the chat remember me?", "Within a conversation, yes: city, dates, budget and so on. A new chat starts empty. You can edit or clear what it remembers from the chips above the message box."],
  ["Is real money involved?", "Not by default. The ledger and merchants are simulated. An optional testnet mode exists but is untested end to end."],
  ["Is it audited or certified?", "No. It is a hackathon prototype. Please do not use real funds."],
  ["Which browsers work?", "Current Chrome, Edge, Safari and Firefox on devices that support passkeys."],
  ["How do I report a security issue?", <>Use the <Link href="/contact">contact page</Link>.</>],
];

export default function FAQ() {
  return (
    <Page eyebrow="FAQ" title="Frequently asked questions">
      <div className="faq">
        {faqs.map(([q, a]) => (<details key={q}><summary>{q}</summary><p>{a}</p></details>))}
      </div>
    </Page>
  );
}
