// Where each role lands after sign-in. Supervisors use the Android app and suppliers get a portal later
// (Stage 8), so neither has a web home yet.
export type Role = "client" | "contractor" | "supervisor" | "supplier" | "ops";

const HOME: Partial<Record<string, string>> = {
  client: "/projects",
  contractor: "/c",
  ops: "/ops",
};

export function homeFor(role: string): string | null {
  return HOME[role] ?? null;
}

/** Where a signed-out visitor signs in: staff at /ops/sign-in (WEB-OPS-001), everyone else at /sign-in. */
export function signInPathFor(next: string, expired = false): string {
  const page = next === "/ops" || next.startsWith("/ops/") ? "/ops/sign-in" : "/sign-in";
  return `${page}?next=${encodeURIComponent(next)}${expired ? "&expired=1" : ""}`;
}

/**
 * A safe place to return to after sign-in: a path on this site, not another origin ("//evil.example",
 * "/\evil.example") and not an API route.
 */
export function safeNext(value: string | null | undefined, fallback = "/"): string {
  if (!value || !value.startsWith("/") || value.startsWith("//") || value.startsWith("/\\")) return fallback;
  if (value === "/api" || value.startsWith("/api/")) return fallback;
  return value;
}
