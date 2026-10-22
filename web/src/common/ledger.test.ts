import { describe, expect, it } from "vitest";

import { escrowNow, ledgerCsv, moneyByMilestone, readLedger, type LedgerEntry } from "./ledger";

const P = "project-1";
let n = 0;
const entry = (over: Partial<LedgerEntry>): LedgerEntry => ({
  id: `e${++n}`,
  transaction_id: `t${n}`,
  account: "",
  direction: "debit",
  amount_minor: 0,
  currency: "NGN",
  fx_rate: null,
  ref_type: "payment_event",
  ref_id: "",
  created_at: "2026-10-22T05:00:00.000Z",
  ...over,
});

/** The three transactions escrow writes for one held payment (as on the local stack). */
function payment(
  ref: string,
  at: string,
  ngn: number,
  net: number,
  fee = 0,
  currency = "GBP",
): LedgerEntry[] {
  const rate = "1950.0000000000";
  return [
    entry({
      ref_id: ref,
      created_at: at,
      account: `stripe_clearing:${currency}`,
      direction: "debit",
      amount_minor: net + fee,
      currency,
    }),
    entry({
      ref_id: ref,
      created_at: at,
      account: `client_funding:${P}:${currency}`,
      direction: "credit",
      amount_minor: net,
      currency,
    }),
    entry({
      ref_id: ref,
      created_at: at,
      account: `client_funding:${P}:${currency}`,
      direction: "debit",
      amount_minor: net,
      currency,
      fx_rate: rate,
    }),
    entry({
      ref_id: ref,
      created_at: at,
      account: `fx_conversion:${currency}`,
      direction: "credit",
      amount_minor: net,
      currency,
      fx_rate: rate,
    }),
    entry({
      ref_id: ref,
      created_at: at,
      account: `escrow:${P}:NGN`,
      direction: "debit",
      amount_minor: ngn,
      fx_rate: rate,
    }),
    entry({
      ref_id: ref,
      created_at: at,
      account: "fx_conversion:NGN",
      direction: "credit",
      amount_minor: ngn,
      fx_rate: rate,
    }),
  ];
}

function release(ref: string, at: string, ngn: number, payable = "contractor_payable:NGN"): LedgerEntry[] {
  return [
    entry({
      ref_type: "escrow_release",
      ref_id: ref,
      created_at: at,
      account: payable,
      direction: "debit",
      amount_minor: ngn,
    }),
    entry({
      ref_type: "escrow_release",
      ref_id: ref,
      created_at: at,
      account: `escrow:${P}:NGN`,
      direction: "credit",
      amount_minor: ngn,
    }),
  ];
}

const entries = [
  ...payment("pay-1", "2026-10-22T05:09:44.462Z", 232_850_000, 119_411),
  ...release("rel-1", "2026-10-22T05:10:08.881Z", 232_850_000),
  ...payment("pay-2", "2026-10-22T05:10:11.149Z", 645_800_000, 331_180, 500),
];
const milestones = [
  {
    id: "m1",
    status: "released",
    amount_minor: 232_850_000,
    funded_at: "2026-10-22T05:09:44.533Z",
    released_at: "2026-10-22T05:10:08.938Z",
  },
  {
    id: "m2",
    status: "verified",
    amount_minor: 645_800_000,
    funded_at: "2026-10-22T05:10:11.175Z",
    released_at: null,
  },
  { id: "m3", status: "pending", amount_minor: 400_600_000, funded_at: null, released_at: null },
];

describe("readLedger", () => {
  const ledger = readLedger(P, entries);

  it("finds each payment with what was paid, converted and held, and its rate", () => {
    expect(
      ledger.payments.map((p) => [p.ref, p.paidMinor, p.netMinor, p.ngnMinor, p.fxRate, p.held]),
    ).toEqual([
      ["pay-2", 331_680n, 331_180n, 645_800_000n, "1950.0000000000", true],
      ["pay-1", 119_411n, 119_411n, 232_850_000n, "1950.0000000000", true],
    ]);
  });

  it("finds releases and who they pay", () => {
    expect(ledger.releases).toEqual([
      { ref: "rel-1", at: "2026-10-22T05:10:08.881Z", ngnMinor: 232_850_000n, payee: "contractor" },
    ]);
  });

  it("works out what is in escrow now from the escrow account (MX-20)", () => {
    expect(ledger.escrowNgnMinor).toBe(645_800_000n);
  });

  it("keeps a payment the milestone couldn't take as not held", () => {
    const unmatched = readLedger(P, [
      entry({ ref_id: "x", account: "stripe_clearing:GBP", amount_minor: 100, currency: "GBP" }),
      entry({
        ref_id: "x",
        account: `client_funding:${P}:GBP`,
        direction: "credit",
        amount_minor: 100,
        currency: "GBP",
      }),
    ]);
    expect(unmatched.payments[0]).toMatchObject({ held: false, ngnMinor: 0n, fxRate: null });
    expect(unmatched.escrowNgnMinor).toBe(0n);
  });
});

describe("moneyByMilestone", () => {
  const ledger = readLedger(P, entries);
  const money = moneyByMilestone(milestones, ledger);

  it("matches each milestone to the payment held with it and the release that paid it", () => {
    expect(money.get("m1")?.payment?.ref).toBe("pay-1");
    expect(money.get("m1")?.release?.ref).toBe("rel-1");
    expect(money.get("m2")?.payment?.ref).toBe("pay-2");
    expect(money.get("m2")?.release).toBeUndefined();
    expect(money.get("m3")).toEqual({ payment: undefined, release: undefined });
  });

  it("uses the amount to decide between two payments held in the same moment", () => {
    const at = "2026-10-22T06:00:00.000Z";
    const twin = readLedger(P, [...payment("a", at, 100_000, 50), ...payment("b", at, 200_000, 100)]);
    const pair = moneyByMilestone(
      [
        { id: "big", amount_minor: 200_000, funded_at: at, released_at: null },
        { id: "small", amount_minor: 100_000, funded_at: at, released_at: null },
      ],
      twin,
    );
    expect(pair.get("big")?.payment?.ref).toBe("b");
    expect(pair.get("small")?.payment?.ref).toBe("a");
  });

  it("never matches a payment more than a few seconds away", () => {
    const far = moneyByMilestone(
      [{ id: "m", amount_minor: 232_850_000, funded_at: "2026-10-22T05:12:00Z", released_at: null }],
      ledger,
    );
    expect(far.get("m")?.payment).toBeUndefined();
  });
});

describe("escrowNow", () => {
  it("gives NGN and the client amount still held", () => {
    const ledger = readLedger(P, entries);
    expect(escrowNow(milestones, ledger, moneyByMilestone(milestones, ledger))).toEqual({
      ngnMinor: 645_800_000n,
      client: { amountMinor: 331_180n, currency: "GBP" },
    });
  });

  it("gives NGN only when a held payment can't be matched", () => {
    const ledger = readLedger(P, entries);
    const unmatched = [{ ...milestones[1]!, funded_at: "2026-10-22T09:00:00Z" }];
    expect(escrowNow(unmatched, ledger, moneyByMilestone(unmatched, ledger)).client).toBeNull();
  });
});

describe("ledgerCsv", () => {
  it("writes one line per entry, quoting where needed", () => {
    const csv = ledgerCsv([entry({ account: 'odd,"name"', amount_minor: 5, ref_id: "r" })]);
    const [header, line] = csv.trimEnd().split("\n");
    expect(header).toBe(
      "created_at_utc,transaction_id,account,direction,amount_minor,currency,fx_rate,ref_type,ref_id",
    );
    expect(line).toContain('"odd,""name"""');
    expect(line).toContain(",5,NGN,,payment_event,r");
  });
});
