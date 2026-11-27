// The pure parts of ops' side of contractor matching (ADR 0007, phase 2): who is on the shortlist and in what
// order, and what the statuses are called. Mirrors the backend: 1 to 3 contractors, each once, in the order
// the client sees them.

export const SHORTLIST_MAX = 3;

export type MatchStatus = "open" | "shortlisted" | "matched" | "cancelled";

export const MATCH_STATUS: Record<MatchStatus, { label: string; tone: "warn" | "ok" | "neutral" }> = {
  open: { label: "Waiting for a shortlist", tone: "warn" },
  shortlisted: { label: "Shortlist sent", tone: "ok" },
  matched: { label: "Matched", tone: "ok" },
  cancelled: { label: "Cancelled", tone: "neutral" },
};

/** Add a contractor to the shortlist (at the end, up to three) or take them off. */
export function toggleChoice(selected: readonly string[], id: string): string[] {
  if (selected.includes(id)) return selected.filter((s) => s !== id);
  return selected.length >= SHORTLIST_MAX ? [...selected] : [...selected, id];
}

export function canSend(selected: readonly string[]): boolean {
  return selected.length >= 1 && selected.length <= SHORTLIST_MAX;
}

/** Move a contractor one place up (-1) or down (+1) in the order the client sees. */
export function move(selected: readonly string[], id: string, by: -1 | 1): string[] {
  const from = selected.indexOf(id);
  const to = from + by;
  if (from < 0 || to < 0 || to >= selected.length) return [...selected];
  const next = [...selected];
  [next[from], next[to]] = [next[to]!, next[from]!];
  return next;
}

/** True when ops may still change the request (nothing is decided yet). */
export function isActive(status: string): boolean {
  return status === "open" || status === "shortlisted";
}
