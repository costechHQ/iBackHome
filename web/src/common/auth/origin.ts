import type { NextRequest } from "next/server";

/**
 * A URL on this site for a redirect, built from the host the browser used. In Docker the server binds to
 * HOSTNAME=0.0.0.0 and Next builds `req.url` from it, so `new URL(path, req.url)` sent people to
 * http://0.0.0.0:3000/..., which browsers refuse. Behind Caddy the same bug would leak the internal address.
 * Same header order as isSameOrigin (common/api/http.ts).
 */
export function siteUrl(req: NextRequest, path: string): URL {
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  if (!host) return new URL(path, req.nextUrl);
  const proto =
    req.headers.get("x-forwarded-proto")?.split(",")[0]?.trim() || req.nextUrl.protocol.slice(0, -1);
  try {
    return new URL(path, `${proto}://${host}`);
  } catch {
    return new URL(path, req.nextUrl);
  }
}
