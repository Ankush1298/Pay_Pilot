/**
 * One place for everything you need to fill in before launch.
 * TODO(before launch): replace the placeholder contact details, social URLs and domain below.
 */
export const site = {
  name: "PayPilot",
  tagline: "The AI proposes. The policy decides. Your passkey approves.",
  description:
    "PayPilot is a security gateway for AI agents that spend money: every payment is checked by a policy engine and sensitive ones need your passkey.",
  // Set NEXT_PUBLIC_SITE_URL in production. Used for the sitemap, Open Graph and canonical links.
  url: process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000",
  contact: {
    email: "hello@example.com", // TODO: real address
    phone: "+00 000 000 0000", // TODO: real phone (or delete it from Contact and the footer)
    address: "Your Street 0, Your City, Your Country", // TODO: real postal address
    hours: "Mon–Fri, 10:00–18:00 (your time zone)", // TODO
  },
  social: {
    github: "https://github.com/", // TODO: repo or org URL
    twitter: "https://x.com/", // TODO
    linkedin: "https://www.linkedin.com/", // TODO
  },
  legalLastUpdated: "2026-10-06",
  // TODO(lawyer): legal pages are plain-language drafts that describe what the app does today.
  // They have not been reviewed by a lawyer. Do not launch publicly before they are.
} as const;

export const nav = [
  { href: "/#features", label: "Features" },
  { href: "/#how", label: "How it works" },
  { href: "/security", label: "Security" },
  { href: "/demo", label: "Demo" },
] as const;

export const footerColumns = [
  { title: "Product", links: [["Features", "/#features"], ["How it works", "/#how"], ["Live demo", "/demo"], ["Security", "/security"]] },
  { title: "Company", links: [["About", "/about"], ["Contact", "/contact"], ["FAQ", "/faq"]] },
  { title: "Legal", links: [["Privacy Policy", "/privacy"], ["Terms & Conditions", "/terms"], ["Cookie Policy", "/cookies"]] },
  { title: "Resources", links: [["FAQ", "/faq"], ["Threat model", "/security#threats"], ["Sign in", "/login"], ["Create account", "/register"]] },
] as const;
