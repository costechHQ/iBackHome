import { describe, expect, it } from "vitest";

import { boqAsQuoteText, counts, flaggedFirst, overIndexTotal, times } from "./quote";

const line = (flag: string, extra: object = {}) => ({
  item: flag,
  unit: "bag",
  quantity: "420.000",
  unit_price_minor: 1_150_000,
  line_total_minor: 483_000_000,
  flag,
  index_price_minor: 980_000,
  ...extra,
});

describe("quote checker", () => {
  it("writes each BoQ line with its quantity and unit price together", () => {
    const text = boqAsQuoteText([
      {
        sequence: 1,
        name: "Foundation",
        items: [
          {
            line_no: 2,
            description: "Cement, 50 kg bag",
            unit: "bag",
            quantity: "420.000",
            unit_price_minor: 1_150_000,
          },
        ],
      },
    ]);
    expect(text).toBe("1.2 Cement, 50 kg bag: 420.000 bag at NGN 11500.00 each");
  });

  it("puts flagged lines first and counts each kind", () => {
    const lines = [line("within_index"), line("not_in_index"), line("over_index")];
    expect(flaggedFirst(lines).map((l) => l.flag)).toEqual(["over_index", "not_in_index", "within_index"]);
    expect(counts(lines)).toEqual({ over: 1, within: 1, notInIndex: 1 });
  });

  it("multiplies decimal quantities by kobo without floats", () => {
    expect(times("420.000", 170_000)).toBe(71_400_000n);
    expect(times("1.5", 333)).toBe(500n); // 499.5 rounds half up
    expect(times("48", 650_000)).toBe(31_200_000n);
  });

  it("adds up what the over-index lines cost above the index", () => {
    // (11,500 − 9,800) × 420 = ₦714,000
    expect(overIndexTotal([line("over_index"), line("within_index")])).toBe(71_400_000n);
  });
});
