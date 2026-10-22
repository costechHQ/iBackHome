import "server-only";

import { apiBaseUrl } from "./backend";
import type { TokenPair } from "./cookies";

// Single-flight refresh (ADR 0004). The backend rotates the refresh token once and treats any reuse as theft:
// it revokes every session of that user. So for one refresh token we call POST /auth/refresh at most once:
//  - callers that arrive while it runs share the same promise;
//  - callers that arrive shortly after (a page whose requests were already in flight with the old cookie)
//    get the same result from a short cache instead of reusing the old token;
//  - a failure is cached too and never retried; the user signs in again.
// The cache lives in this process. That is correct for the single web container on staging; more than one
// web instance needs a shared lock and cache (for example Redis) first.

export const REUSE_WINDOW_MS = 30_000;

export class RefreshFailed extends Error {
  constructor(readonly code: string) {
    super(`Refresh failed: ${code}`);
    this.name = "RefreshFailed";
  }
}

type Entry = { promise: Promise<TokenPair>; settledAt: number | null };

const inFlight = new Map<string, Entry>();

export async function callBackendRefresh(refreshToken: string): Promise<TokenPair> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}/api/v1/auth/refresh`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
      cache: "no-store",
    });
  } catch {
    // We don't know whether the backend rotated the token. Never retry: treat the session as ended.
    throw new RefreshFailed("network_error");
  }
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as { error?: { code?: string } } | null;
    throw new RefreshFailed(body?.error?.code ?? `http_${response.status}`);
  }
  return (await response.json()) as TokenPair;
}

export function refreshSession(
  refreshToken: string,
  {
    now = Date.now,
    refresh = callBackendRefresh,
  }: { now?: () => number; refresh?: typeof callBackendRefresh } = {},
): Promise<TokenPair> {
  for (const [token, entry] of inFlight) {
    if (entry.settledAt !== null && now() - entry.settledAt > REUSE_WINDOW_MS) inFlight.delete(token);
  }
  const existing = inFlight.get(refreshToken);
  if (existing) return existing.promise;

  const entry: Entry = { promise: refresh(refreshToken), settledAt: null };
  const settle = () => {
    entry.settledAt = now();
  };
  entry.promise.then(settle, settle);
  inFlight.set(refreshToken, entry);
  return entry.promise;
}

/** For tests only. */
export function resetRefreshCache(): void {
  inFlight.clear();
}
