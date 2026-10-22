import "server-only";

// Where the web server reaches FastAPI: inside Docker http://api:8000, locally http://127.0.0.1:8000.
export function apiBaseUrl(): string {
  return (process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

/**
 * The caller's IP for the backend's per-IP limits. On staging Caddy sets X-Forwarded-For to the client;
 * we pass on only the last entry (the one the hop in front of us added), never a chain the browser could forge.
 */
export function callerIp(headers: Headers): string | null {
  const last = headers.get("x-forwarded-for")?.split(",").pop()?.trim();
  return last || null;
}
