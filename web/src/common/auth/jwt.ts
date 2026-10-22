// Reads a JWT's expiry WITHOUT verifying it. Only used to decide whether to refresh before calling the backend;
// the backend verifies every token on every request, so a forged `exp` gains nothing.

export function tokenExpiry(token: string | undefined): number | null {
  const payload = token?.split(".")[1];
  if (!payload) return null;
  try {
    const json = JSON.parse(atob(payload.replace(/-/g, "+").replace(/_/g, "/"))) as { exp?: unknown };
    return typeof json.exp === "number" ? json.exp : null;
  } catch {
    return null;
  }
}

/** True when the token is missing, unreadable or expires within `skewSeconds`. */
export function needsRefresh(token: string | undefined, nowSeconds: number, skewSeconds = 30): boolean {
  const exp = tokenExpiry(token);
  return exp === null || exp - skewSeconds <= nowSeconds;
}
