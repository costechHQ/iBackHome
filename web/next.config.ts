import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The Docker image runs the standalone server (`node server.js`); the Dockerfile sets NEXT_STANDALONE=1.
  // CI and local runs use `next build` + `next start`, which doesn't support standalone output.
  // A static export is never an option: it can't serve the auth proxy.
  output: process.env.NEXT_STANDALONE === "1" ? "standalone" : undefined,
  poweredByHeader: false,
  reactStrictMode: true,
};

export default nextConfig;
