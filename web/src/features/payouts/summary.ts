// What the contractor's payouts page (WEB-CONTRACTOR-008) shows, worked out from the milestones of each of
// their projects (NGN only). Each released milestone is paid to the contractor's account by the escrow partner;
// the transfer's own reference and status need payout history (MX-06), so a row says "Released".

type M = {
  id: string;
  name: string;
  sequence: number;
  status: string;
  amount_minor: number;
  released_at?: string | null;
};
type P = { id: string; title: string };

export type PayoutStage = "not_funded" | "held" | "releasing" | "paused" | "released";

const STAGE: Record<string, PayoutStage> = {
  pending: "not_funded",
  funded: "held",
  claimed: "held",
  verified: "held",
  approved: "releasing",
  disputed: "paused",
  released: "released",
};

export type PayoutRow = {
  id: string;
  projectId: string;
  projectTitle: string;
  milestone: string;
  sequence: number;
  amountMinor: bigint;
  stage: PayoutStage;
  releasedAt: string | null;
};

export type PayoutSummary = {
  received: { minor: bigint; count: number; projects: number };
  held: { minor: bigint; names: string[] };
  notFunded: { minor: bigint; names: string[] };
  rows: PayoutRow[];
};

const ORDER: Record<PayoutStage, number> = { not_funded: 0, paused: 1, releasing: 2, held: 3, released: 4 };

/** Totals and one row per milestone: still to come first (by project and sequence), then released, newest first. */
export function payoutSummary(projects: readonly { project: P; milestones: readonly M[] }[]): PayoutSummary {
  const rows: PayoutRow[] = projects.flatMap(({ project, milestones }) =>
    milestones.map((m) => ({
      id: m.id,
      projectId: project.id,
      projectTitle: project.title,
      milestone: m.name,
      sequence: m.sequence,
      amountMinor: BigInt(m.amount_minor),
      stage: STAGE[m.status] ?? "not_funded",
      releasedAt: m.released_at ?? null,
    })),
  );
  rows.sort((a, b) => {
    if (a.stage === "released" && b.stage === "released") {
      return (b.releasedAt ?? "").localeCompare(a.releasedAt ?? "");
    }
    return (
      ORDER[a.stage] - ORDER[b.stage] ||
      a.projectTitle.localeCompare(b.projectTitle) ||
      a.sequence - b.sequence
    );
  });
  const sum = (stages: PayoutStage[]) => rows.filter((r) => stages.includes(r.stage));
  const total = (list: PayoutRow[]) => list.reduce((s, r) => s + r.amountMinor, 0n);
  const released = sum(["released"]);
  const held = sum(["held", "releasing", "paused"]);
  const notFunded = sum(["not_funded"]);
  return {
    received: {
      minor: total(released),
      count: released.length,
      projects: new Set(released.map((r) => r.projectId)).size,
    },
    held: { minor: total(held), names: held.map((r) => r.milestone) },
    notFunded: { minor: total(notFunded), names: notFunded.map((r) => r.milestone) },
    rows,
  };
}

/** "Plastering" or "Plastering and Roofing" or "Plastering and 2 more". */
export function namesText(names: readonly string[]): string {
  if (names.length <= 2) return names.join(" and ");
  return `${names[0]} and ${names.length - 1} more`;
}
