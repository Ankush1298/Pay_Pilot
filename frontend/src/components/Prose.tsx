import { site } from "@/config/site";

/** Shared shell for text pages. */
export function Page({ eyebrow, title, lead, children }: { eyebrow?: string; title: string; lead?: string; children: React.ReactNode }) {
  return (
    <div className="container section narrow">
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 className="page-title">{title}</h1>
      {lead && <p className="section-lead">{lead}</p>}
      {children}
    </div>
  );
}

/** Legal pages: dated, and flagged for lawyer review in the source and on the page. */
export function Legal({ title, children }: { title: string; children: React.ReactNode }) {
  // TODO(lawyer): this text describes what the app does today in plain language. It has NOT been reviewed by a lawyer.
  // Have it reviewed (and localised for your jurisdiction) before any public launch.
  return (
    <Page eyebrow="Legal" title={title}>
      <p className="legal-meta">Last updated: {new Date(site.legalLastUpdated).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}</p>
      <p className="legal-warn" role="note">This is a hackathon prototype. These texts are plain-language drafts that describe how the app works today and have not been reviewed by a lawyer.</p>
      <div className="prose">{children}</div>
    </Page>
  );
}
