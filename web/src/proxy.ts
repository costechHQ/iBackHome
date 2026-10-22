import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_COOKIE, SESSION_COOKIE } from "./common/auth/cookies";
import { needsRefresh } from "./common/auth/jwt";

// Next's request proxy (the file once called middleware), for the signed-in portals only. It doesn't check
// roles (each route-group layout does, from GET /me) and holds no state: Next may run it apart from the rest
// of the server. It only routes:
//  - no session at all            -> /sign-in?next=<this page>
//  - access token (nearly) expired -> /api/session/refresh?next=<this page>, which refreshes once and comes back
// The API proxy under /api/v1 refreshes by itself and is not matched here.

export function proxy(req: NextRequest) {
  const next = `${req.nextUrl.pathname}${req.nextUrl.search}`;

  if (!req.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(new URL(`/sign-in?next=${encodeURIComponent(next)}`, req.url));
  }
  if (needsRefresh(req.cookies.get(ACCESS_COOKIE)?.value, Math.floor(Date.now() / 1000), 60)) {
    return NextResponse.redirect(new URL(`/api/session/refresh?next=${encodeURIComponent(next)}`, req.url));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/home", "/projects/:path*", "/c", "/c/:path*", "/ops", "/ops/:path*"],
};
