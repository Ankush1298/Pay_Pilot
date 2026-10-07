import Link from "next/link";
import { site } from "@/config/site";

export function Logo() {
  return (
    <Link href="/" className="logo" aria-label={`${site.name} home`}>
      <svg width="28" height="28" viewBox="0 0 32 32" aria-hidden="true">
        <rect width="32" height="32" rx="8" fill="var(--accent)" />
        <circle cx="16" cy="16" r="8" fill="none" stroke="var(--text-inverse)" strokeWidth="2" />
        <path d="M12.5 16.2l2.4 2.4 4.8-5" fill="none" stroke="var(--text-inverse)" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
      <span>{site.name}</span>
    </Link>
  );
}
