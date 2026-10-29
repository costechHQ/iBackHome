// Session cookies (ADR 0004). All httpOnly, so browser JavaScript never sees a token.
//   ibh_at  access token, sent to pages and the API proxy, lives as long as the token (15 min)
//   ibh_rt  refresh token, sent only to /api (the API proxy and /api/session/*), never with a page
//   ibh_s   "a session exists" flag with no secret, so src/proxy.ts can tell "signed out" from "token expired"
// SameSite=Lax rather than Strict: links from WhatsApp and email must arrive signed in. Writes are also
// protected by the Origin check in the API proxy.

export const ACCESS_COOKIE = "ibh_at";
export const REFRESH_COOKIE = "ibh_rt";
export const SESSION_COOKIE = "ibh_s";

// The backend's refresh token lifetime (REFRESH_TOKEN_DAYS, 30 by default). The backend is the authority:
// a cookie that outlives its token just leads to one failed refresh and a sign-in.
export const REFRESH_MAX_AGE_SECONDS = 30 * 24 * 60 * 60;

// Secure everywhere except the local Docker stack (IBH_ENVIRONMENT=local, set only in docker-compose.yml). Browsers
// accept Secure cookies on http://localhost and http://127.0.0.1, but a phone opening the dev server by its LAN
// address (http://192.168.x.x:3000) refuses them, so sign-in appeared to work and then kept no session. Unset or
// any other value stays Secure.
const base = {
  httpOnly: true,
  get secure() {
    return process.env.IBH_ENVIRONMENT !== "local";
  },
  sameSite: "lax" as const,
};

export type TokenPair = { access_token: string; refresh_token: string; expires_in: number };

type CookieJar = {
  set(name: string, value: string, options: Record<string, unknown>): unknown;
};

export function setSessionCookies(jar: CookieJar, tokens: TokenPair): void {
  jar.set(ACCESS_COOKIE, tokens.access_token, { ...base, path: "/", maxAge: tokens.expires_in });
  jar.set(REFRESH_COOKIE, tokens.refresh_token, { ...base, path: "/api", maxAge: REFRESH_MAX_AGE_SECONDS });
  jar.set(SESSION_COOKIE, "1", { ...base, path: "/", maxAge: REFRESH_MAX_AGE_SECONDS });
}

export function clearSessionCookies(jar: CookieJar): void {
  jar.set(ACCESS_COOKIE, "", { ...base, path: "/", maxAge: 0 });
  jar.set(REFRESH_COOKIE, "", { ...base, path: "/api", maxAge: 0 });
  jar.set(SESSION_COOKIE, "", { ...base, path: "/", maxAge: 0 });
}
