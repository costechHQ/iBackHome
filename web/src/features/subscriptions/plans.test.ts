import { describe, expect, it } from "vitest";

import { PLAN_BLURB, PUBLIC_PLANS, visitsLabel } from "./plans";

describe("supervision plans", () => {
  it("offers Basic, Standard and Premium at $100, $150 and $200 in US dollars", () => {
    expect(PUBLIC_PLANS.map((p) => [p.code, p.amount_minor, p.currency])).toEqual([
      ["basic", 10_000, "USD"],
      ["standard", 15_000, "USD"],
      ["premium", 20_000, "USD"],
    ]);
  });

  it("gives 2, 3 and 4 site visits a month, and recommends Standard only", () => {
    expect(PUBLIC_PLANS.map((p) => p.visits_per_month)).toEqual([2, 3, 4]);
    expect(PUBLIC_PLANS.filter((p) => p.recommended).map((p) => p.code)).toEqual(["standard"]);
  });

  it("words the visits and has a blurb for every plan", () => {
    expect(visitsLabel(3)).toBe("3 site visits a month");
    for (const p of PUBLIC_PLANS) expect(PLAN_BLURB[p.code].length).toBeGreaterThan(0);
  });
});
