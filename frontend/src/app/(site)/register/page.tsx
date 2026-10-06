import type { Metadata } from "next";
import { AuthForm } from "@/components/AuthForms";

export const metadata: Metadata = { title: "Create account", description: "Create a passkey-only PayPilot account. No password, no seed phrase." };
export default function Page() { return <AuthForm mode="register" />; }
