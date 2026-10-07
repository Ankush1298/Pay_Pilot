import { Footer } from "@/components/Footer";
import { Navbar } from "@/components/Navbar";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return (
    <>
      <Navbar />
      <main id="main" tabIndex={-1}>{children}</main>
      <Footer />
    </>
  );
}
