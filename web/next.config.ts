import type { NextConfig } from "next";

// 127.0.0.1, not "localhost": on Windows "localhost" resolves to IPv6 first and the API
// listens on IPv4, which can add seconds per connection in some clients.
const API_URL = process.env.API_URL ?? "http://127.0.0.1:8000";

const nextConfig: NextConfig = {
  // Separate build folders for `next dev` and production builds: building while the dev
  // server runs would otherwise overwrite its files (slow recompiles, broken pages).
  distDir: process.env.NEXT_DIST_DIR ?? ".next",
  output: "standalone", // small self-contained server for Docker
  poweredByHeader: false,
  devIndicators: false, // hide the floating "N" dev-tools button

  // The browser only talks to this origin. /api/v1/* is proxied to FastAPI, so no CORS
  // and the backend URL never reaches the client. /api/auth/* is handled by Next itself
  // (it sets the httpOnly refresh-token cookie).
  async rewrites() {
    return [{ source: "/api/v1/:path*", destination: `${API_URL}/:path*` }];
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
        ],
      },
    ];
  },
};

export default nextConfig;
