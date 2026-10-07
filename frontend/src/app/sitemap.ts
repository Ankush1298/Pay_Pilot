import type { MetadataRoute } from "next";
import { site } from "@/config/site";

const paths = ["", "/demo", "/security", "/about", "/contact", "/faq", "/privacy", "/terms", "/cookies", "/login", "/register"];

export default function sitemap(): MetadataRoute.Sitemap {
  return paths.map((p) => ({ url: `${site.url}${p}`, lastModified: new Date(site.legalLastUpdated), changeFrequency: "monthly", priority: p === "" ? 1 : 0.6 }));
}
