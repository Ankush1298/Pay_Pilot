import type { Metadata } from "next";
import { AuthForm } from "@/components/AuthForms";

export const metadata: Metadata = { title: "Log in", description: "Sign in to PayPilot with your passkey." };
export default function Page() { return <AuthForm mode="login" />; }
