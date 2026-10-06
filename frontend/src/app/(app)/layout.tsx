import { AppLayout } from "@/components/AppLayout";
import { Footer } from "@/components/Footer";

export default function AppSectionLayout({ children }: { children: React.ReactNode }) {
  return (
    <AppLayout>
      <div id="main" tabIndex={-1}>{children}</div>
      <Footer />
    </AppLayout>
  );
}
