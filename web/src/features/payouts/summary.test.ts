import { describe, expect, it } from "vitest";

import { namesText, payoutSummary } from "./summary";

const m = (
  id: string,
  sequence: number,
  status: string,
  amount: number,
  released_at: string | null = null,
) => ({
  id,
  name: `M${sequence}`,
  sequence,
  status,
  amount_minor: amount,
  released_at,
});

describe("payout summary", () => {
  const summary = payoutSummary([
    {
      project: { id: "p1", title: "Bungalow" },
      milestones: [
        m("a", 1, "released", 1_000, "2026-11-06T11:20:00Z"),
        m("b", 2, "released", 2_000, "2026-11-27T09:14:00Z"),
        m("c", 3, "claimed", 300),
        m("d", 4, "pending", 40),
      ],
    },
    {
      project: { id: "p2", title: "Duplex" },
      milestones: [m("e", 1, "disputed", 5), m("f", 2, "approved", 7), m("g", 3, "pending", 9)],
    },
  ]);

  it("adds released, held and not-yet-funded money in integer kobo", () => {
    expect(summary.received).toEqual({ minor: 3_000n, count: 2, projects: 1 });
    expect(summary.held).toEqual({ minor: 312n, names: ["M1", "M2", "M3"] });
    expect(summary.notFunded.minor).toBe(49n);
  });

  it("lists what is still to come first, then released milestones newest first", () => {
    expect(summary.rows.map((r) => `${r.id}:${r.stage}`)).toEqual([
      "d:not_funded",
      "g:not_funded",
      "e:paused",
      "f:releasing",
      "c:held",
      "b:released",
      "a:released",
    ]);
  });

  it("is empty with no projects", () => {
    expect(payoutSummary([]).received.minor).toBe(0n);
  });
});

describe("names", () => {
  it("shortens long lists", () => {
    expect(namesText(["Roof"])).toBe("Roof");
    expect(namesText(["Roof", "Walls"])).toBe("Roof and Walls");
    expect(namesText(["Roof", "Walls", "Floor"])).toBe("Roof and 2 more");
  });
});
