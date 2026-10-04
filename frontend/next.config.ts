import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://127.0.0.1:8000/api/:path*",
      },
      {
        source: "/merchant/:path*",
        destination: "http://127.0.0.1:8000/merchant/:path*",
      },
      {
        source: "/merchants",
        destination: "http://127.0.0.1:8000/merchants",
      },
    ];
  },
};

export default nextConfig;
