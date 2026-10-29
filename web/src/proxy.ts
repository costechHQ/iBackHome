import { NextResponse, type NextRequest } from "next/server";

import { ACCESS_COOKIE, SESSION_COOKIE } from "./common/auth/cookies";
import { needsRefresh } from "./common/auth/jwt";
import { siteUrl } from "./common/auth/origin";
import { signInPathFor } from "./common/auth/roles";

// Next's request proxy (the file once called middleware), for the signed-in portals only. It doesn't check
// roles (each route-group layout does, from GET /me) and holds no state: Next may run it apart from the rest
// of the server. It only routes:
//  - no session at all            -> /sign-in?next=<this page> (/ops/sign-in for the ops console)
//  - access token (nearly) expired -> /api/session/refresh?next=<this page>, which refreshes once and comes back
// The API proxy under /api/v1 refreshes by itself and is not matched here. The public landing page "/" is
// matched only to send a signed-in visitor to /home (which picks their portal); signed out, it's served as is.

export function proxy(req: NextRequest) {
  if (req.nextUrl.pathname === "/") {
    return req.cookies.has(SESSION_COOKIE)
      ? NextResponse.redirect(siteUrl(req, "/home"))
      : NextResponse.next();
  }
  // The ops sign-in page sits under /ops but is for signed-out staff.
  if (req.nextUrl.pathname === "/ops/sign-in") return NextResponse.next();
  const next = `${req.nextUrl.pathname}${req.nextUrl.search}`;

  if (!req.cookies.has(SESSION_COOKIE)) {
    return NextResponse.redirect(siteUrl(req, signInPathFor(next)));
  }
  if (needsRefresh(req.cookies.get(ACCESS_COOKIE)?.value, Math.floor(Date.now() / 1000), 60)) {
    return NextResponse.redirect(siteUrl(req, `/api/session/refresh?next=${encodeURIComponent(next)}`));
  }
  return NextResponse.next();
}

export const config = {
  matcher: ["/", "/home", "/welcome", "/projects/:path*", "/c", "/c/:path*", "/ops", "/ops/:path*"],
};
