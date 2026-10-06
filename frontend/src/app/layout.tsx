import type { Metadata } from "next";
import { ClientProviders } from "./ClientProviders";
import "./globals.css";

export const metadata: Metadata = {
  title: "PayPilot — AI Payment Security",
  description:
    "The AI proposes. The policy decides. You approve. Secure AI transaction layer with passkey verification.",
  openGraph: {
    title: "PayPilot",
    description: "Secure AI payment layer with policy-engine enforcement and passkey approvals.",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <meta name="theme-color" content="#f4f7f8" />
      </head>
      <body>
        <ClientProviders>
          {children}
        </ClientProviders>
      </body>
    </html>
  );
}
