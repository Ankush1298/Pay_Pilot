import type { Metadata } from "next";
import Link from "next/link";
import { StepUpDemo } from "@/components/StepUpDemo";

export const metadata: Metadata = { title: "Demo", description: "Try PayPilot's allow, step-up and block decisions in a simulation." };

export default function Page() {
  return (
    <div className="container section narrow">
      <p className="eyebrow">Interactive demo</p>
      <h1 className="page-title">Three payments, three outcomes</h1>
      <p className="section-lead">Pick a scenario to see what the policy engine decides and what you would be asked to do.</p>
      <StepUpDemo />
      <p className="text-center" style={{ marginTop: "2rem" }}><Link href="/register" className="btn btn-primary btn-lg">Try it for real with a passkey</Link></p>
    </div>
  );
}
