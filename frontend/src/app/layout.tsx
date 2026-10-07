import type { Metadata, Viewport } from "next";
import { ClientProviders } from "./ClientProviders";
import { site } from "@/config/site";
import "@fontsource-variable/inter";
import "@fontsource/jetbrains-mono";
import "./globals.css";
import "./site.css";

export const metadata: Metadata = {
  metadataBase: new URL(site.url),
  title: { default: `${site.name}: AI payment security with passkeys`, template: `%s · ${site.name}` },
  description: site.description,
  applicationName: site.name,
  openGraph: { title: site.name, description: site.description, type: "website", siteName: site.name, url: site.url },
  twitter: { card: "summary_large_image", title: site.name, description: site.description },
};

export const viewport: Viewport = { themeColor: "#fbf3df", width: "device-width", initialScale: 1 };

// Applies a saved theme before first paint (only exists if the visitor allowed preference storage).
const themeScript = `try{var t=localStorage.getItem('pp_theme_v2');if(t==='light'||t==='dark')document.documentElement.dataset.theme=t}catch(e){}`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" data-theme="light" suppressHydrationWarning>
      <head><script dangerouslySetInnerHTML={{ __html: themeScript }} /></head>
      <body>
        <a href="#main" className="skip-link">Skip to content</a>
        <ClientProviders>{children}</ClientProviders>
      </body>
    </html>
  );
}
