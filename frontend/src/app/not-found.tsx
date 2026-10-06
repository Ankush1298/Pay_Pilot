import Link from "next/link";
import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";

export default function NotFound() {
  return (
    <>
      <Navbar />
      <main id="main" tabIndex={-1} className="container section narrow text-center">
        <p className="eyebrow">404</p>
        <h1 className="page-title">This page could not be found</h1>
        <p className="section-lead">The link may be old, or the page moved.</p>
        <p><Link href="/" className="btn btn-primary">Back to home</Link></p>
      </main>
      <Footer />
    </>
  );
}
