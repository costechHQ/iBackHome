// Reads a project's ledger (GET /projects/{id}/ledger) into what the screens show: payments, releases, the
// money in escrow now (MX-20), and which payment and release belong to which milestone. Everything is in integer
// minor units (bigint for sums) and fx_rate stays a decimal string.
//
// How escrow writes the ledger (backend features/escrow/service.py):
//  - a client payment is up to three transactions sharing one ref (ref_type payment_event): received
//    (stripe_clearing debit, client_funding:{project}:{CUR} credit, gross), converted (client_funding debit,
//    the net amount, with fx_rate) and held (escrow:{project}:NGN debit, with fx_rate). A payment the milestone
//    couldn't take ("unmatched") has only the first one.
//  - a release is one transaction (ref_type escrow_release): escrow:{project}:NGN credit, payable debit.
// Ledger entries don't name their milestone (gap MX-27). A milestone's payment is the one held within a few
// seconds of its funded_at (the same database transaction), its release the one within a few seconds of its
// released_at; the amount breaks a tie. All in one place, so MX-27 replaces it cleanly.

export type LedgerEntry = {
  id: string;
  transaction_id: string;
  account: string;
  direction: string;
  amount_minor: number;
  currency: string;
  fx_rate: string | null;
  ref_type: string;
  ref_id: string;
  created_at: string;
};

export type Payment = {
  ref: string;
  at: string;
  /** What the client paid, fee included, in their currency. */
  paidMinor: bigint;
  /** What was converted for the milestone, in their currency. */
  netMinor: bigint;
  currency: string;
  /** NGN held in escrow (0 when the payment wasn't held). */
  ngnMinor: bigint;
  fxRate: string | null;
  held: boolean;
};

export type Release = {
  ref: string;
  at: string;
  ngnMinor: bigint;
  payee: "contractor" | "supplier" | "other";
};

export type ProjectLedger = {
  payments: Payment[];
  releases: Release[];
  /** NGN in escrow now: escrow:{project}:NGN debits minus credits (MX-20). */
  escrowNgnMinor: bigint;
};

const MATCH_WINDOW_MS = 5_000;

const ms = (iso: string) => new Date(iso).getTime();

export function readLedger(projectId: string, entries: readonly LedgerEntry[]): ProjectLedger {
  const escrowAccount = `escrow:${projectId}:NGN`;
  const clientFunding = `client_funding:${projectId}:`;
  let escrowNgnMinor = 0n;
  const byPayment = new Map<string, LedgerEntry[]>();
  const byRelease = new Map<string, LedgerEntry[]>();

  for (const e of entries) {
    if (e.account === escrowAccount) {
      escrowNgnMinor += e.direction === "debit" ? BigInt(e.amount_minor) : -BigInt(e.amount_minor);
    }
    const bucket =
      e.ref_type === "payment_event" ? byPayment : e.ref_type === "escrow_release" ? byRelease : null;
    if (bucket) bucket.set(e.ref_id, [...(bucket.get(e.ref_id) ?? []), e]);
  }

  const payments: Payment[] = [];
  for (const [ref, group] of byPayment) {
    const received = group.find((e) => e.account.startsWith(clientFunding) && e.direction === "credit");
    if (!received) continue; // not a client payment into this project
    const converted = group.find((e) => e.account.startsWith(clientFunding) && e.direction === "debit");
    const held = group.find((e) => e.account === escrowAccount && e.direction === "debit");
    const gross = group.find((e) => e.account.startsWith("stripe_clearing:") && e.direction === "debit");
    payments.push({
      ref,
      at: (held ?? received).created_at,
      paidMinor: BigInt((gross ?? received).amount_minor),
      netMinor: BigInt((converted ?? received).amount_minor),
      currency: received.currency,
      ngnMinor: held ? BigInt(held.amount_minor) : 0n,
      fxRate: held?.fx_rate ?? converted?.fx_rate ?? null,
      held: Boolean(held),
    });
  }

  const releases: Release[] = [];
  for (const [ref, group] of byRelease) {
    const out = group.find((e) => e.account === escrowAccount && e.direction === "credit");
    if (!out) continue;
    const payable = group.find((e) => e.direction === "debit")?.account ?? "";
    releases.push({
      ref,
      at: out.created_at,
      ngnMinor: BigInt(out.amount_minor),
      payee: payable.startsWith("contractor_payable")
        ? "contractor"
        : payable.startsWith("supplier_payable")
          ? "supplier"
          : "other",
    });
  }

  const newestFirst = (a: { at: string }, b: { at: string }) => ms(b.at) - ms(a.at);
  return { payments: payments.sort(newestFirst), releases: releases.sort(newestFirst), escrowNgnMinor };
}

type MilestoneTimes = {
  id: string;
  amount_minor: number;
  funded_at: string | null;
  released_at: string | null;
};

function closest<T extends { at: string }>(
  candidates: readonly T[],
  when: string | null,
  amount: bigint,
  amountOf: (c: T) => bigint,
  used: Set<T>,
): T | undefined {
  if (!when) return undefined;
  const near = candidates.filter((c) => !used.has(c) && Math.abs(ms(c.at) - ms(when)) <= MATCH_WINDOW_MS);
  near.sort(
    (a, b) =>
      Number(amountOf(b) === amount) - Number(amountOf(a) === amount) ||
      Math.abs(ms(a.at) - ms(when)) - Math.abs(ms(b.at) - ms(when)),
  );
  const match = near[0];
  if (match) used.add(match);
  return match;
}

export type MilestoneMoney = { payment?: Payment; release?: Release };

/** Which held payment and which contractor release belong to each milestone (see the header comment). */
export function moneyByMilestone(
  milestones: readonly MilestoneTimes[],
  ledger: ProjectLedger,
): Map<string, MilestoneMoney> {
  const usedPayments = new Set<Payment>();
  const usedReleases = new Set<Release>();
  const held = ledger.payments.filter((p) => p.held);
  const contractor = ledger.releases.filter((r) => r.payee === "contractor");
  const result = new Map<string, MilestoneMoney>();
  for (const m of milestones) {
    const amount = BigInt(m.amount_minor);
    result.set(m.id, {
      payment: closest(held, m.funded_at, amount, (p) => p.ngnMinor, usedPayments),
      release: closest(contractor, m.released_at, amount, (r) => r.ngnMinor, usedReleases),
    });
  }
  return result;
}

export type EscrowNow = {
  ngnMinor: bigint;
  /** The client-currency amount of the payments still held, when every held milestone was matched. */
  client: { amountMinor: bigint; currency: string } | null;
};

/** "In escrow now" (MX-20): NGN from the escrow account; the client amount from the payments not yet released. */
export function escrowNow(
  milestones: readonly (MilestoneTimes & { status: string })[],
  ledger: ProjectLedger,
  money: Map<string, MilestoneMoney>,
): EscrowNow {
  const stillHeld = milestones.filter((m) => m.funded_at && m.status !== "released");
  const payments = stillHeld.map((m) => money.get(m.id)?.payment);
  const currencies = new Set(payments.map((p) => p?.currency));
  const client =
    payments.length && payments.every(Boolean) && currencies.size === 1
      ? {
          amountMinor: payments.reduce((sum, p) => sum + (p?.netMinor ?? 0n), 0n),
          currency: payments[0]!.currency,
        }
      : null;
  return { ngnMinor: ledger.escrowNgnMinor, client };
}

const csvCell = (value: string) => (/[",\n]/.test(value) ? `"${value.replace(/"/g, '""')}"` : value);

/** The ledger as CSV (MX-22, made in the browser): one line per entry, exactly as the API returned it. */
export function ledgerCsv(entries: readonly LedgerEntry[]): string {
  const header = [
    "created_at_utc",
    "transaction_id",
    "account",
    "direction",
    "amount_minor",
    "currency",
    "fx_rate",
    "ref_type",
    "ref_id",
  ];
  const lines = entries.map((e) =>
    [
      e.created_at,
      e.transaction_id,
      e.account,
      e.direction,
      String(e.amount_minor),
      e.currency,
      e.fx_rate ?? "",
      e.ref_type,
      e.ref_id,
    ]
      .map(csvCell)
      .join(","),
  );
  return [header.join(","), ...lines].join("\n") + "\n";
}
