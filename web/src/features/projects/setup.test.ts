import { describe, expect, it } from "vitest";

import { doneCount, nextAction, setupSteps } from "./setup";

const draft = { status: "draft", contractor_id: "c", supervisor_id: null, site: null };

describe("project set-up", () => {
  it("counts what is done", () => {
    expect(doneCount(setupSteps(draft, null))).toBe(2);
    const sited = { ...draft, site: {}, supervisor_id: "s" };
    expect(doneCount(setupSteps(sited, null))).toBe(4);
    const active = { ...sited, status: "active" };
    expect(doneCount(setupSteps(active, null, [{ status: "pending" }]))).toBe(5);
    expect(doneCount(setupSteps(active, null, [{ status: "funded" }]))).toBe(6);
  });

  it("says what to do next", () => {
    expect(nextAction(draft, null)?.kind).toBe("site");
    expect(nextAction({ ...draft, site: {} }, null)).toEqual({
      kind: "wait",
      label: "Waiting for your contractor's BoQ",
    });
    const review = { ...draft, site: {}, status: "boq_review" };
    expect(nextAction(review, { approvals_missing: ["client", "ops"] })?.kind).toBe("review_boq");
    expect(nextAction(review, { approvals_missing: ["ops"] })?.label).toBe("Waiting for the other approvals");
    expect(nextAction({ ...review, status: "active" }, null, [{ status: "pending" }])?.kind).toBe("fund");
    expect(nextAction({ ...review, status: "active" }, null, [{ status: "funded" }])).toBeNull();
  });
});
