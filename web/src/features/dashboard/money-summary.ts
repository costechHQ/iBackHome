// A project's money at a glance, for the client home (WEB-CLIENT-008) and the overview (009): released, held in
// escrow now, not yet funded and the BoQ total, in naira, plus the client's currency where every payment
// involved was matched to its milestone (common/ledger.ts). Integers only.

import {
  escrowNow,
  moneyByMilestone,
  type EscrowNow,
  type MilestoneMoney,
  type ProjectLedger,
} from "@/common/ledger";

type M = {
  id: string;
  status: string;
  amount_minor: number;
  funded_at: string | null;
  released_at: string | null;
};

export type ClientAmount = { amountMinor: bigint; currency: string };

export type MoneySummary = {
  money: Map<string, MilestoneMoney>;
  boqNgn: bigint;
  releasedNgn: bigint;
  releasedClient: ClientAmount | null;
  notFundedNgn: bigint;
  escrow: EscrowNow;
};

function sum(ms: readonly M[]): bigint {
  return ms.reduce((s, m) => s + BigInt(m.amount_minor), 0n);
}

export function moneySummary(milestones: readonly M[], ledger: ProjectLedger): MoneySummary {
  const money = moneyByMilestone(milestones, ledger);
  const released = milestones.filter((m) => m.status === "released");
  const payments = released.map((m) => money.get(m.id)?.payment);
  const currencies = new Set(payments.map((p) => p?.currency));
  const releasedClient =
    payments.length && payments.every(Boolean) && currencies.size === 1
      ? {
          amountMinor: payments.reduce((s, p) => s + (p?.netMinor ?? 0n), 0n),
          currency: payments[0]!.currency,
        }
      : null;
  return {
    money,
    boqNgn: sum(milestones),
    releasedNgn: sum(released),
    releasedClient,
    notFundedNgn: sum(milestones.filter((m) => m.status === "pending")),
    escrow: escrowNow(milestones, ledger, money),
  };
}
