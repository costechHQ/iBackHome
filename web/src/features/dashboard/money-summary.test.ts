import { describe, expect, it } from "vitest";

import type { ProjectLedger } from "@/common/ledger";

import { moneySummary } from "./money-summary";

const t = (s: number) => new Date(Date.UTC(2026, 9, 1, 10, 0, s)).toISOString();

const milestones = [
  { id: "a", status: "released", amount_minor: 1_000_000, funded_at: t(0), released_at: t(30) },
  { id: "b", status: "funded", amount_minor: 2_000_000, funded_at: t(10), released_at: null },
  { id: "c", status: "pending", amount_minor: 3_000_000, funded_at: null, released_at: null },
];

const payment = (at: string, ngn: number, net: number) => ({
  ref: at,
  at,
  paidMinor: BigInt(net + 10),
  netMinor: BigInt(net),
  currency: "GBP",
  ngnMinor: BigInt(ngn),
  fxRate: "2000",
  held: true,
});

const ledger: ProjectLedger = {
  payments: [payment(t(0), 1_000_000, 500), payment(t(10), 2_000_000, 1_000)],
  releases: [{ ref: "r", at: t(30), ngnMinor: 1_000_000n, payee: "contractor" }],
  escrowNgnMinor: 2_000_000n,
};

describe("money summary", () => {
  it("adds up released, held and unfunded naira", () => {
    const s = moneySummary(milestones, ledger);
    expect(s.boqNgn).toBe(6_000_000n);
    expect(s.releasedNgn).toBe(1_000_000n);
    expect(s.notFundedNgn).toBe(3_000_000n);
    expect(s.escrow.ngnMinor).toBe(2_000_000n);
  });

  it("gives the client's currency when every payment matched", () => {
    const s = moneySummary(milestones, ledger);
    expect(s.releasedClient).toEqual({ amountMinor: 500n, currency: "GBP" });
    expect(s.escrow.client).toEqual({ amountMinor: 1_000n, currency: "GBP" });
  });

  it("gives naira only when a payment can't be matched", () => {
    const s = moneySummary(milestones, { ...ledger, payments: [] });
    expect(s.releasedClient).toBeNull();
    expect(s.escrow.client).toBeNull();
  });
});
