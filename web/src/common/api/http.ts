import "server-only";

import { NextResponse, type NextRequest } from "next/server";

/** Every authenticated or proxied answer: never stored by the browser, Next or anything in between. */
export const NO_STORE = "no-store";

export function errorResponse(status: number, code: string, message: string): NextResponse {
  return NextResponse.json({ error: { code, message } }, { status, headers: { "Cache-Control": NO_STORE } });
}

/**
 * CSRF guard for writes: the browser's Origin must be this site. Cross-site pages can't forge Origin, and they
 * can't send X-Forwarded-Host without a preflight that these routes never answer.
 */
export function isSameOrigin(req: NextRequest): boolean {
  const origin = req.headers.get("origin");
  const host = req.headers.get("x-forwarded-host") ?? req.headers.get("host");
  if (!origin || !host) return false;
  try {
    return new URL(origin).host === host;
  } catch {
    return false;
  }
}
