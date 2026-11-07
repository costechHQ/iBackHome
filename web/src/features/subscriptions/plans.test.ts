import { describe, expect, it } from "vitest";

import { billedLabel, freeMonthsLabel, PLAN_BLURB, periodPrices, PUBLIC_PLANS, visitsLabel } from "./plans";

describe("supervision plans", () => {
  it("offers Basic, Standard and Premium at $100, $150 and $200 in US dollars", () => {
    expect(PUBLIC_PLANS.map((p) => [p.code, p.amount_minor, p.currency])).toEqual([
      ["basic", 10_000, "USD"],
      ["standard", 15_000, "USD"],
      ["premium", 20_000, "USD"],
    ]);
  });

  it("gives 2, 3 and 4 site visits a month, and recommends Premium only", () => {
    expect(PUBLIC_PLANS.map((p) => p.visits_per_month)).toEqual([2, 3, 4]);
    expect(PUBLIC_PLANS.filter((p) => p.recommended).map((p) => p.code)).toEqual(["premium"]);
  });

  it("words the visits and has a blurb for every plan", () => {
    expect(visitsLabel(3)).toBe("3 site visits a month");
    for (const p of PUBLIC_PLANS) expect(PLAN_BLURB[p.code].length).toBeGreaterThan(0);
  });

  it("prices bi-annual at 5 months for 6 and annual at 10 months for 12", () => {
    const prices = periodPrices(20_000);
    const [monthly, biannual, annual] = prices;
    expect(monthly).toMatchObject({ months: 1, paid_months: 1, amount_minor: 20_000 });
    expect(biannual).toMatchObject({
      months: 6,
      paid_months: 5,
      amount_minor: 100_000,
      list_amount_minor: 120_000,
    });
    expect(annual).toMatchObject({
      months: 12,
      paid_months: 10,
      amount_minor: 200_000,
      list_amount_minor: 240_000,
    });
    expect(prices.map((p) => p.monthly_equivalent_minor)).toEqual([20_000, 16_666, 16_666]);
  });

  it("carries the same three periods on every public plan", () => {
    expect(PUBLIC_PLANS.map((p) => p.periods?.map((x) => x.amount_minor))).toEqual([
      [10_000, 50_000, 100_000],
      [15_000, 75_000, 150_000],
      [20_000, 100_000, 200_000],
    ]);
  });

  it("words the free months and the billing interval", () => {
    const prices = periodPrices(10_000);
    expect(prices.map(freeMonthsLabel)).toEqual(["", "1 month free", "2 months free"]);
    expect(prices.map(billedLabel)).toEqual([
      "billed every month",
      "billed every 6 months",
      "billed every year",
    ]);
  });
});
