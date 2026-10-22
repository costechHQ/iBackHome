import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import { errorResponse, isSameOrigin, NO_STORE } from "../api/http";
import { apiBaseUrl, callerIp } from "./backend";
import {
  ACCESS_COOKIE,
  clearSessionCookies,
  REFRESH_COOKIE,
  setSessionCookies,
  type TokenPair,
} from "./cookies";
import { refreshSession } from "./refresh";
import { homeFor, safeNext } from "./roles";

// Route handler logic for /api/session/* (the route files in app/api/session/ only call these).

/** POST /api/session/verify {identifier, code}: exchange the login code, keep the tokens in cookies. */
export async function verifyOtp(req: NextRequest): Promise<NextResponse> {
  if (!isSameOrigin(req))
    return errorResponse(403, "cross_origin_request", "This request didn't come from iBackHome.");

  let input: { identifier?: unknown; code?: unknown };
  try {
    input = (await req.json()) as typeof input;
  } catch {
    return errorResponse(422, "validation_error", "Send your phone number or email and the 6-digit code.");
  }

  const headers = new Headers({ "content-type": "application/json" });
  const ip = callerIp(req.headers);
  if (ip) headers.set("x-forwarded-for", ip);

  let upstream: Response;
  try {
    upstream = await fetch(`${apiBaseUrl()}/api/v1/auth/otp/verify`, {
      method: "POST",
      headers,
      body: JSON.stringify({ identifier: input.identifier, code: input.code }),
      cache: "no-store",
    });
  } catch {
    return errorResponse(502, "upstream_unreachable", "We couldn't reach iBackHome. Try again.");
  }
  if (!upstream.ok) {
    // The backend's own error (invalid_code, otp_expired, too_many_attempts, ...); it never contains a token.
    return new NextResponse(upstream.body, {
      status: upstream.status,
      headers: { "content-type": "application/json", "Cache-Control": NO_STORE },
    });
  }

  const tokens = (await upstream.json()) as TokenPair;
  const me = await fetch(`${apiBaseUrl()}/api/v1/me`, {
    headers: { authorization: `Bearer ${tokens.access_token}` },
    cache: "no-store",
  }).catch(() => null);
  const role = me?.ok ? ((await me.json()) as { role: string }).role : null;

  const response = NextResponse.json(
    { role, home: role ? homeFor(role) : null },
    { headers: { "Cache-Control": NO_STORE } },
  );
  setSessionCookies(response.cookies, tokens);
  return response;
}

/**
 * GET /api/session/refresh?next=/path: src/proxy.ts sends a page request here when the access token is about
 * to expire (server components can't set cookies, so pages never refresh themselves). Refreshes once, sets
 * the new cookies and goes back; on failure ends the session and opens sign-in.
 */
export async function refreshAndReturn(req: NextRequest): Promise<NextResponse> {
  const next = safeNext(req.nextUrl.searchParams.get("next"));
  const refreshToken = req.cookies.get(REFRESH_COOKIE)?.value;
  const signIn = new URL(`/sign-in?next=${encodeURIComponent(next)}&expired=1`, req.nextUrl);

  if (refreshToken) {
    try {
      const tokens = await refreshSession(refreshToken);
      const response = NextResponse.redirect(new URL(next, req.nextUrl), 303);
      response.headers.set("Cache-Control", NO_STORE);
      setSessionCookies(response.cookies, tokens);
      return response;
    } catch {
      // Fall through: the session is over.
    }
  }
  const response = NextResponse.redirect(signIn, 303);
  response.headers.set("Cache-Control", NO_STORE);
  clearSessionCookies(response.cookies);
  return response;
}

/**
 * POST /api/session/sign-out: forget the session on this browser. The backend has no sign-out endpoint yet
 * (MX-19), so the refresh token stays valid on the server until it expires.
 */
export function signOut(req: NextRequest): NextResponse {
  if (!isSameOrigin(req))
    return errorResponse(403, "cross_origin_request", "This request didn't come from iBackHome.");
  const response = new NextResponse(null, { status: 204, headers: { "Cache-Control": NO_STORE } });
  clearSessionCookies(response.cookies);
  return response;
}

/**
 * GET /home: "Go to my projects" from anywhere (error pages don't know who is signed in). Sends the person to
 * their portal's home, or to sign-in. src/proxy.ts refreshes the token first. Supervisors and suppliers have
 * no web portal yet and land on the client page's 403, which says so.
 */
export async function goHome(req: NextRequest): Promise<NextResponse> {
  const token = req.cookies.get(ACCESS_COOKIE)?.value;
  let role: string | null = null;
  if (token) {
    const me = await fetch(`${apiBaseUrl()}/api/v1/me`, {
      headers: { authorization: `Bearer ${token}` },
      cache: "no-store",
    }).catch(() => null);
    role = me?.ok ? ((await me.json()) as { role: string }).role : null;
  }
  const target = role ? (homeFor(role) ?? "/projects") : "/sign-in";
  const response = NextResponse.redirect(new URL(target, req.nextUrl), 303);
  response.headers.set("Cache-Control", NO_STORE);
  return response;
}
