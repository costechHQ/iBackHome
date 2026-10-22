import { describe, expect, it } from "vitest";

import {
  currentMilestone,
  heldMinor,
  isSentBack,
  needsContractor,
  notReady,
  releasedMinor,
} from "./contractor";

const rejected = {
  decision: "rejected",
  checklist: [{ passed: true }, { passed: false }, { passed: false }],
  notes: "Fix the cracks",
  created_at: "2026-10-22T06:00:00Z",
};
const ms = [
  { id: "a", sequence: 1, status: "released", amount_minor: 100 },
  { id: "b", sequence: 2, status: "funded", amount_minor: 200, latest_verification: rejected },
  { id: "c", sequence: 3, status: "claimed", amount_minor: 300 },
  { id: "d", sequence: 4, status: "pending", amount_minor: 400 },
];

describe("contractor milestones", () => {
  it("knows a milestone sent back for rework from the latest verification", () => {
    expect(ms.map(isSentBack)).toEqual([false, true, false, false]);
    // A rejection followed by a new claim is no longer "sent back".
    expect(isSentBack({ ...ms[1]!, status: "claimed" })).toBe(false);
  });

  it("counts the checklist items that aren't ready", () => {
    expect(notReady(ms[1]!)).toEqual({ notReady: 2, total: 3 });
    expect(notReady({ ...ms[1]!, latest_verification: { ...rejected, checklist: [] } })).toBeNull();
  });

  it("adds up NGN held and released, in integers", () => {
    expect(heldMinor(ms)).toBe(500n);
    expect(releasedMinor(ms)).toBe(100n);
  });

  it("finds the milestone being worked on and what needs the contractor", () => {
    expect(currentMilestone(ms)?.id).toBe("b");
    expect(needsContractor(ms).map((m) => m.id)).toEqual(["b"]);
  });
});
