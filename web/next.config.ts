import type { NextConfig } from "next";

// Signed-in portals and every API route: never stored by a browser or a shared cache (ADR 0004). The pages are
// rendered per request anyway; this makes the rule explicit and covers redirects and errors too.
const NO_STORE = [{ key: "Cache-Control", value: "no-store" }];
const PRIVATE_PATHS = [
  "/home",
  "/welcome",
  "/projects/:path*",
  "/c/:path*",
  "/ops/:path*",
  "/sign-in",
  "/api/:path*",
];

const nextConfig: NextConfig = {
  // The Docker image runs the standalone server (`node server.js`); the Dockerfile sets NEXT_STANDALONE=1.
  // CI and local runs use `next build` + `next start`, which doesn't support standalone output.
  // A static export is never an option: it can't serve the auth proxy.
  output: process.env.NEXT_STANDALONE === "1" ? "standalone" : undefined,
  poweredByHeader: false,
  reactStrictMode: true,
  async headers() {
    return PRIVATE_PATHS.map((source) => ({ source, headers: NO_STORE }));
  },
};

export default nextConfig;
