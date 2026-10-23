import { describe, expect, it } from "vitest";

import { assignFit, openChecks, splitSpotChecks, spotCheckFit, watDateTime } from "./supervision";

describe("vetting checks", () => {
  it("lists what is still open; approval needs all four", () => {
    const none = {
      registration_verified: false,
      nin_verified: false,
      guarantor_1_verified: false,
      guarantor_2_verified: false,
    };
    expect(openChecks(none)).toHaveLength(4);
    expect(
      openChecks({ ...none, registration_verified: true, nin_verified: true, guarantor_1_verified: true }),
    ).toEqual(["guarantor_2_verified"]);
    expect(
      openChecks({
        registration_verified: true,
        nin_verified: true,
        guarantor_1_verified: true,
        guarantor_2_verified: true,
      }),
    ).toEqual([]);
  });
});

describe("who may take a project", () => {
  const base = { user_id: "s", account_status: "active", assigned_here: false, related_to_contractor: false };

  it("blocks relatives of the contractor, the current supervisor and suspended accounts", () => {
    expect(assignFit(base)).toEqual({ ok: true });
    expect(assignFit({ ...base, related_to_contractor: true })).toEqual({
      ok: false,
      reason: "Related to the contractor",
    });
    expect(assignFit({ ...base, assigned_here: true }).ok).toBe(false);
    expect(assignFit({ ...base, account_status: "suspended" }).ok).toBe(false);
  });

  it("never lets the project's own supervisor spot-check it", () => {
    expect(spotCheckFit({ ...base, assigned_here: true })).toEqual({
      ok: false,
      reason: "The project’s own supervisor",
    });
    expect(spotCheckFit({ ...base, related_to_contractor: true }).ok).toBe(false);
    expect(spotCheckFit(base).ok).toBe(true);
  });
});

describe("spot-check times", () => {
  it("reads a day and time in WAT as one moment with its offset", () => {
    expect(watDateTime("2026-10-30", "10:30")).toBe("2026-10-30T10:30:00+01:00");
    expect(new Date(watDateTime("2026-10-30", "10:30")!).toISOString()).toBe("2026-10-30T09:30:00.000Z");
    expect(watDateTime("30/10/2026", "10:30")).toBeNull();
    expect(watDateTime("2026-10-30", "")).toBeNull();
  });

  it("splits upcoming (soonest first) from done (latest first)", () => {
    const { upcoming, done } = splitSpotChecks([
      { scheduled_for: "2026-11-02T09:00:00Z", completed_at: null },
      { scheduled_for: "2026-11-01T09:00:00Z", completed_at: null },
      { scheduled_for: "2026-10-01T09:00:00Z", completed_at: "2026-10-01T12:00:00Z" },
      { scheduled_for: "2026-10-05T09:00:00Z", completed_at: "2026-10-05T12:00:00Z" },
    ]);
    expect(upcoming.map((c) => c.scheduled_for.slice(5, 10))).toEqual(["11-01", "11-02"]);
    expect(done.map((c) => c.completed_at!.slice(5, 10))).toEqual(["10-05", "10-01"]);
  });
});
