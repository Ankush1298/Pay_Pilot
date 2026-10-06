import { ImageResponse } from "next/og";
import { site } from "@/config/site";

export const alt = `${site.name}: ${site.tagline}`;
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default function OG() {
  return new ImageResponse(
    (
      <div style={{ width: "100%", height: "100%", display: "flex", flexDirection: "column", justifyContent: "center", padding: 80, background: "#080d10", color: "#e8f0f3" }}>
        <div style={{ fontSize: 40, color: "#2dd4bf", fontWeight: 700 }}>{site.name}</div>
        <div style={{ fontSize: 76, fontWeight: 800, lineHeight: 1.1, marginTop: 24 }}>{site.tagline}</div>
        <div style={{ fontSize: 30, color: "#a3b4bb", marginTop: 32 }}>Passkey-approved, policy-checked AI payments</div>
      </div>
    ),
    size,
  );
}
