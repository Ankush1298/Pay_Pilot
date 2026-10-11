import type { NextConfig } from "next";

const isProd = process.env.NODE_ENV === "production";
// Where the FastAPI backend runs. On Vercel set BACKEND_URL (e.g. https://paypilot-api.onrender.com), no trailing slash.
const backend = (process.env.BACKEND_URL ?? "http://127.0.0.1:8001").replace(/\/$/, "");

// Next.js needs inline scripts/styles for hydration; everything else is locked to this origin.
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isProd ? "" : " 'unsafe-eval'"}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self' data:",
  "connect-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "Referrer-Policy", value: "no-referrer" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
  { key: "Strict-Transport-Security", value: "max-age=31536000; includeSubDomains" },
];

const nextConfig: NextConfig = {
  poweredByHeader: false,
  allowedDevOrigins: ["9d4e-220-158-144-22.ngrok-free.app"],
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${backend}/api/:path*`,
      },
      {
        source: "/merchant/:path*",
        destination: `${backend}/merchant/:path*`,
      },
      {
        source: "/merchants",
        destination: `${backend}/merchants`,
      },
    ];
  },
};

export default nextConfig;
