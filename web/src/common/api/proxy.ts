import "server-only";

import { NextResponse, type NextRequest } from "next/server";

import { apiBaseUrl, callerIp } from "../auth/backend";
import {
  ACCESS_COOKIE,
  clearSessionCookies,
  REFRESH_COOKIE,
  setSessionCookies,
  type TokenPair,
} from "../auth/cookies";
import { needsRefresh } from "../auth/jwt";
import { refreshSession } from "../auth/refresh";
import { errorResponse, isSameOrigin, NO_STORE } from "./http";

// The same-origin API proxy (ADR 0003): the browser calls /api/v1/*, we call FastAPI with the bearer token
// from the httpOnly cookie. Tokens never appear in a response body or reach browser JavaScript.

// These answer with tokens; only /api/session/* may call them.
const BLOCKED = new Set(["auth/otp/verify", "auth/refresh"]);
// No session needed (and a stale session must not get in the way of signing in again).
const PUBLIC_PREFIX = "auth/";
const SAFE_METHODS = new Set(["GET", "HEAD"]);
const MAX_BODY_BYTES = 1_000_000;
const REQUEST_HEADERS = ["accept", "content-type", "idempotency-key", "x-request-id"];
const RESPONSE_HEADERS = ["content-type", "retry-after", "x-request-id"];

export async function proxyToApi(req: NextRequest, segments: string[]): Promise<NextResponse> {
  const path = segments.map(encodeURIComponent).join("/");
  if (BLOCKED.has(path)) return errorResponse(404, "not_found", "Not found.");

  const method = req.method.toUpperCase();
  if (!SAFE_METHODS.has(method) && !isSameOrigin(req)) {
    return errorResponse(403, "cross_origin_request", "This request didn't come from iBackHome.");
  }

  let body: ArrayBuffer | undefined;
  if (!SAFE_METHODS.has(method)) {
    body = await req.arrayBuffer();
    if (body.byteLength > MAX_BODY_BYTES) {
      return errorResponse(413, "payload_too_large", "The request is too large.");
    }
  }

  const isPublic = path.startsWith(PUBLIC_PREFIX);
  const refreshToken = isPublic ? undefined : req.cookies.get(REFRESH_COOKIE)?.value;
  let accessToken = isPublic ? undefined : req.cookies.get(ACCESS_COOKIE)?.value;
  let rotated: TokenPair | null = null;

  const refresh = async (token: string): Promise<boolean> => {
    try {
      rotated = await refreshSession(token);
      accessToken = rotated.access_token;
      return true;
    } catch {
      return false;
    }
  };

  if (refreshToken && needsRefresh(accessToken, Math.floor(Date.now() / 1000))) {
    if (!(await refresh(refreshToken))) return sessionEnded();
  }

  const send = () => {
    const headers = new Headers();
    for (const name of REQUEST_HEADERS) {
      const value = req.headers.get(name);
      if (value) headers.set(name, value);
    }
    const ip = callerIp(req.headers);
    if (ip) headers.set("x-forwarded-for", ip);
    if (accessToken) headers.set("authorization", `Bearer ${accessToken}`);
    return fetch(`${apiBaseUrl()}/api/v1/${path}${req.nextUrl.search}`, {
      method,
      headers,
      body,
      cache: "no-store",
      redirect: "manual",
    });
  };

  let upstream: Response;
  try {
    upstream = await send();
    // The access token was rejected although it looked valid: refresh once and replay once. Replaying a write
    // is safe because it carries the same Idempotency-Key.
    if (upstream.status === 401 && refreshToken && !rotated) {
      if (!(await refresh(refreshToken))) return sessionEnded();
      upstream = await send();
    }
  } catch {
    return errorResponse(502, "upstream_unreachable", "We couldn't reach iBackHome. Nothing was changed.");
  }

  const headers = new Headers({ "Cache-Control": NO_STORE });
  for (const name of RESPONSE_HEADERS) {
    const value = upstream.headers.get(name);
    if (value) headers.set(name, value);
  }
  const response = new NextResponse(upstream.body, { status: upstream.status, headers });
  if (rotated) setSessionCookies(response.cookies, rotated);
  return response;
}

function sessionEnded(): NextResponse {
  const response = errorResponse(401, "session_expired", "Please sign in again.");
  clearSessionCookies(response.cookies);
  return response;
}
