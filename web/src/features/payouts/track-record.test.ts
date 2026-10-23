import { describe, expect, it } from "vitest";

import { trackRecord } from "./track-record";

describe("track record", () => {
  it("counts only what the platform recorded on the contractor's projects", () => {
    const record = trackRecord([
      {
        project: { status: "active" },
        milestones: [
          { status: "released" },
          { status: "released" },
          { status: "verified" },
          { status: "funded", latest_verification: { decision: "rejected" } },
          { status: "funded", latest_verification: null },
          { status: "pending" },
        ],
      },
      { project: { status: "boq_review" }, milestones: [] },
      { project: { status: "completed" }, milestones: [{ status: "released" }] },
    ]);
    expect(record).toEqual({
      verified: 4,
      released: 3,
      sentBackNow: 1,
      projects: { active: 1, settingUp: 1, completed: 1 },
    });
  });
});
