"use client";

import Link from "next/link";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main id="main" className="container section narrow text-center">
      <p className="eyebrow">Something went wrong</p>
      <h1 className="page-title">We hit an unexpected error</h1>
      <p className="section-lead">Nothing was charged. You can try again, or head back home.</p>
      {error.digest && <p className="mono text-muted">Reference: {error.digest}</p>}
      <p className="flex gap-2" style={{ justifyContent: "center" }}>
        <button className="btn btn-primary" onClick={reset}>Try again</button>
        <Link href="/" className="btn btn-secondary">Home</Link>
      </p>
    </main>
  );
}
