import type { Metadata } from "next";
import { ContactForm } from "@/components/ContactForm";
import { Page } from "@/components/Prose";
import { site } from "@/config/site";

export const metadata: Metadata = { title: "Contact", description: "Get in touch with the PayPilot team." };

export default function Contact() {
  const c = site.contact;
  return (
    <Page eyebrow="Contact" title="Talk to us" lead="Questions, feedback or security reports are welcome.">
      <div className="contact-grid">
        <ContactForm />
        <aside className="card contact-info">
          <h2>Details</h2>
          <dl>
            <dt>Email</dt><dd><a href={`mailto:${c.email}`}>{c.email}</a></dd>
            <dt>Phone</dt><dd><a href={`tel:${c.phone.replace(/\s/g, "")}`}>{c.phone}</a></dd>
            <dt>Address</dt><dd>{c.address}</dd>
            <dt>Hours</dt><dd>{c.hours}</dd>
          </dl>
          {/* TODO: replace the placeholders in src/config/site.ts */}
        </aside>
      </div>
    </Page>
  );
}
