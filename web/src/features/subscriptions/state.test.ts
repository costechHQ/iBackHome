import { describe as suite, expect, it } from "vitest";

import { describe, needsSubscription } from "./state";

const base = { status: "active", cancel_at_period_end: false, paused_by_billing: false } as const;

suite("subscription state", () => {
  it("offers a start when there is none, or it never completed, or it ended", () => {
    expect(describe(null).canStart).toBe(true);
    expect(describe({ ...base, status: "incomplete" }).canStart).toBe(true);
    expect(describe({ ...base, status: "canceled" }).canStart).toBe(true);
  });

  it("never offers a second checkout while one is running", () => {
    expect(describe(base).canStart).toBe(false);
    expect(describe({ ...base, status: "past_due" }).canStart).toBe(false);
    expect(describe({ ...base, cancel_at_period_end: true }).canStart).toBe(false);
  });

  it("lets the client cancel only an active one that is not already ending", () => {
    expect(describe(base).canCancel).toBe(true);
    expect(describe({ ...base, cancel_at_period_end: true }).canCancel).toBe(false);
    expect(describe({ ...base, status: "past_due" }).canCancel).toBe(false);
    expect(describe(null).canCancel).toBe(false);
  });

  it("says work is paused only when billing paused it", () => {
    const paused = describe({ ...base, status: "past_due", paused_by_billing: true });
    expect(paused.tone).toBe("bad");
    expect(paused.detail).toContain("paused");
    expect(describe({ ...base, status: "past_due" }).detail).not.toContain("is paused");
  });

  it("recognises the BoQ gate error", () => {
    expect(needsSubscription("subscription_required")).toBe(true);
    expect(needsSubscription("site_not_set")).toBe(false);
    expect(needsSubscription(null)).toBe(false);
  });
});
