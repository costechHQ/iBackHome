// The pure parts of W8b (WEB-OPS-003, 004, 007): which vetting checks are still open, who may take or
// spot-check a project, and the spot-check time ops pick in WAT. Mirrors the backend's rules
// (features/supervision): approval needs all four checks; a supervisor related to the contractor can't be
// assigned or spot-check; a spot check is by someone other than the project's supervisor, in the future.

export type VettingChecks = {
  registration_verified: boolean;
  nin_verified: boolean;
  guarantor_1_verified: boolean;
  guarantor_2_verified: boolean;
};

export const CHECK_LABELS: Record<keyof VettingChecks, string> = {
  registration_verified: "Registration checked on the register",
  nin_verified: "NIN matched",
  guarantor_1_verified: "First guarantor confirmed by phone",
  guarantor_2_verified: "Second guarantor confirmed by phone",
};

/** The checks not yet ticked, in the order the page shows them; approval needs none left. */
export function openChecks(checks: VettingChecks): (keyof VettingChecks)[] {
  return (Object.keys(CHECK_LABELS) as (keyof VettingChecks)[]).filter((k) => !checks[k]);
}

type Candidate = {
  user_id: string;
  account_status: string;
  assigned_here?: boolean | null;
  related_to_contractor?: boolean | null;
};

export type Fit = { ok: true } | { ok: false; reason: string };

/** Whether this supervisor can be assigned to the project (the backend re-checks). */
export function assignFit(c: Candidate): Fit {
  if (c.assigned_here) return { ok: false, reason: "Assigned here now" };
  if (c.related_to_contractor) return { ok: false, reason: "Related to the contractor" };
  if (c.account_status !== "active") return { ok: false, reason: "Account suspended" };
  return { ok: true };
}

/** Whether this supervisor can make a spot check on the project: never its own supervisor. */
export function spotCheckFit(c: Candidate): Fit {
  if (c.assigned_here) return { ok: false, reason: "The project’s own supervisor" };
  return assignFit({ ...c, assigned_here: false });
}

/** "2026-10-30" + "10:30" in WAT (UTC+1, no daylight saving) as an ISO time with its offset. */
export function watDateTime(date: string, time: string): string | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || !/^\d{2}:\d{2}$/.test(time)) return null;
  const iso = `${date}T${time}:00+01:00`;
  return Number.isNaN(Date.parse(iso)) ? null : iso;
}

/** Spot checks split into the ones still to make (soonest first) and done (latest first). */
export function splitSpotChecks<T extends { scheduled_for: string; completed_at?: string | null }>(
  checks: readonly T[],
): { upcoming: T[]; done: T[] } {
  return {
    upcoming: checks
      .filter((c) => !c.completed_at)
      .sort((a, b) => a.scheduled_for.localeCompare(b.scheduled_for)),
    done: checks
      .filter((c) => c.completed_at)
      .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? "")),
  };
}
