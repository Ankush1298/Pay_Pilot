import type { Metadata } from "next";
import Link from "next/link";
import { Page } from "@/components/Prose";
import { site } from "@/config/site";

export const metadata: Metadata = { title: "About", description: "Why PayPilot exists and what it is (and is not)." };

export default function About() {
  return (
    <Page eyebrow="About" title="AI that can shop, without holding your wallet" lead={`${site.name} started from one question: if an AI agent can browse and book for you, what stops it from being tricked into paying the wrong person?`}>
      <div className="prose">
        <h2>The idea</h2>
        <p>Agents read web pages, and web pages can lie. A hidden line of text can tell an assistant to &quot;pay this address instead&quot;. So {site.name} treats the AI as an untrusted proposer. It can search, compare and prepare. It cannot approve, and it never holds a key.</p>
        <p>A policy engine, written as ordinary code and kept outside the AI, decides allow, step-up or block. For anything sensitive, you approve with a passkey whose signature covers the exact transaction.</p>
        <h2>What it is today</h2>
        <ul>
          <li>A working prototype: passkey sign-in, an intent and policy engine, a simulated ledger, mock merchants and a Security Lab.</li>
          <li>Open about its limits: it is not audited, the AI is rule-based for the demo, and the default ledger moves no money.</li>
        </ul>
        <h2>What it is not</h2>
        <p>It is not a bank or a wallet, and it holds no real funds. The optional smart-account contract is reference code and is not deployed.</p>
        <p><Link href="/security">Read how the security works</Link> or <Link href="/contact">get in touch</Link>.</p>
      </div>
    </Page>
  );
}
