import { describe, expect, it } from "vitest";

import {
  draftFrom,
  draftTotal,
  emptyLine,
  indexHint,
  issues,
  lineTotal,
  matchIndex,
  parseNaira,
  parseQuantity,
  toSubmit,
  type Draft,
  type IndexEntry,
} from "./boq-draft";

const line = (description: string, unit: string, quantity: string, price: string) => ({
  ...emptyLine(),
  description,
  unit,
  quantity,
  price,
});

const INDEX: IndexEntry[] = [
  {
    item_key: "cement-50kg-bag",
    item: "Cement 50kg bag",
    unit: "bag",
    currency: "NGN",
    price_minor: 1_030_000,
    stale: false,
  },
  {
    item_key: "sharp-sand",
    item: "Sharp sand",
    unit: "tonne",
    currency: "NGN",
    price_minor: 1_850_000,
    stale: false,
  },
  { item_key: "sand", item: "Sand", unit: "tonne", currency: "NGN", price_minor: 1_700_000, stale: false },
];

describe("parsing what the contractor types", () => {
  it("accepts quantities above 0 with up to 3 decimals", () => {
    expect(parseQuantity("12.500")).toBe("12.5");
    expect(parseQuantity("1,000")).toBe("1000");
    expect(parseQuantity("0")).toBeNull();
    expect(parseQuantity("0.000")).toBeNull();
    expect(parseQuantity("1.2345")).toBeNull();
    expect(parseQuantity("-2")).toBeNull();
    expect(parseQuantity("two")).toBeNull();
  });

  it("reads naira into kobo, never through a float", () => {
    expect(parseNaira("10,400")).toBe(1_040_000);
    expect(parseNaira("₦ 10400.5")).toBe(1_040_050);
    expect(parseNaira("0.29")).toBe(29);
    expect(parseNaira("0")).toBeNull();
    expect(parseNaira("1.234")).toBeNull();
  });
});

describe("totals", () => {
  it("rounds each line half up, as the server does", () => {
    // 0.333 × ₦0.15 = 4.995 kobo -> 5
    expect(lineTotal(line("x", "m", "0.333", "0.15"))).toBe(5n);
    expect(lineTotal(line("Cement", "bag", "640", "10,400"))).toBe(665_600_000n);
    expect(lineTotal(line("Cement", "bag", "", "10,400"))).toBeNull();
  });

  it("adds the valid lines of every milestone", () => {
    const d: Draft = {
      milestones: [
        { key: "a", name: "Foundation", lines: [line("Cement", "bag", "2", "100")] },
        {
          key: "b",
          name: "Roof",
          lines: [line("Sheets", "piece", "3", "1,000"), line("Bad", "m", "0", "5")],
        },
      ],
    };
    expect(draftTotal(d)).toBe(20_000n + 300_000n);
  });
});

describe("checks before submitting", () => {
  it("names each problem with the line number, and ignores blank lines", () => {
    const d: Draft = {
      milestones: [
        { key: "a", name: "Foundation", lines: [line("Cement", "bag", "2", "100"), emptyLine()] },
        { key: "b", name: "", lines: [line("Pump hire", "", "0", "450,000")] },
        { key: "c", name: "Roof", lines: [emptyLine()] },
      ],
    };
    expect(issues(d).map((i) => i.label)).toEqual([
      "Milestone 2: give it a name",
      "Line 2.1: choose a unit",
      "Line 2.1: quantity must be more than 0",
      "Milestone 3: add at least one line",
    ]);
  });

  it("passes a complete BoQ, and submits it without totals or blank lines", () => {
    const d: Draft = {
      milestones: [
        { key: "a", name: " Foundation ", lines: [line("Cement", "bag", "2.50", "10,400"), emptyLine()] },
      ],
    };
    expect(issues(d)).toEqual([]);
    expect(toSubmit(d)).toEqual({
      milestones: [
        {
          name: "Foundation",
          items: [{ description: "Cement", unit: "bag", quantity: "2.5", unit_price_minor: 1_040_000 }],
        },
      ],
    });
  });

  it("refuses more than 20 milestones", () => {
    const d: Draft = {
      milestones: Array.from({ length: 21 }, (_, i) => ({
        key: `m${i}`,
        name: `M${i}`,
        lines: [line("Cement", "bag", "1", "1")],
      })),
    };
    expect(issues(d).map((i) => i.label)).toContain("At most 20 milestones");
  });
});

describe("the saved BoQ as a draft", () => {
  it("orders milestones and shows prices in naira", () => {
    const d = draftFrom({
      milestones: [
        { sequence: 2, name: "Roof", items: [] },
        {
          sequence: 1,
          name: "Foundation",
          items: [{ description: "Cement", unit: "bag", quantity: "640.000", unit_price_minor: 1_040_050 }],
        },
      ],
    });
    expect(d.milestones.map((m) => m.name)).toEqual(["Foundation", "Roof"]);
    expect(d.milestones[0]!.lines[0]).toMatchObject({ quantity: "640", price: "10,400.50" });
    expect(draftFrom(null).milestones).toHaveLength(1);
  });
});

describe("price index hint", () => {
  it("matches like the server's quote check", () => {
    expect(matchIndex("Cement 50kg bag", INDEX)?.item).toBe("Cement 50kg bag");
    // "sharp sand" is an exact key; plain "river sand" contains only "sand".
    expect(matchIndex("Sharp sand", INDEX)?.item).toBe("Sharp sand");
    expect(matchIndex("River sand", INDEX)?.item).toBe("Sand");
    expect(matchIndex("Concrete pump hire", INDEX)).toBeNull();
  });

  it("compares the price and flags more than 15% above", () => {
    expect(indexHint(line("Cement 50kg bag", "bag", "1", "10,400"), INDEX)).toMatchObject({
      kind: "priced",
      percent: "1.0",
      over: false,
    });
    expect(indexHint(line("Sharp sand", "tonnes", "4", "22,000"), INDEX)).toMatchObject({
      kind: "priced",
      percent: "18.9",
      over: true,
    });
    expect(indexHint(line("Sharp sand", "tonne", "4", "18,000"), INDEX)).toMatchObject({ percent: "-2.7" });
    expect(indexHint(line("Sharp sand", "bag", "4", "100"), INDEX).kind).toBe("unit_differs");
    expect(indexHint(line("Pump hire", "trip", "1", "100"), INDEX).kind).toBe("none");
  });
});
