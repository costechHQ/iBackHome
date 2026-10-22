// What the contractor's screens need to know about milestones (NGN only: the contractor never sees the client's
// currency). Pure, so the screens and tests share it.

type M = {
  id: string;
  sequence: number;
  status: string;
  amount_minor: number;
  latest_verification?: {
    decision: string;
    checklist: { passed: boolean }[];
    notes?: string | null;
    created_at: string;
  } | null;
};

const HELD = new Set(["funded", "claimed", "verified", "approved", "disputed"]);

/** The supervisor sent the last claim back: the milestone is funded again and needs rework (WEB-CONTRACTOR-006). */
export function isSentBack(m: M): boolean {
  return m.status === "funded" && m.latest_verification?.decision === "rejected";
}

/** "2 of 5 items aren't ready" from the supervisor's checklist; null when they sent it back without one. */
export function notReady(m: M): { notReady: number; total: number } | null {
  const checklist = m.latest_verification?.checklist ?? [];
  if (!checklist.length) return null;
  return { notReady: checklist.filter((i) => !i.passed).length, total: checklist.length };
}

/** NGN still in escrow for this contractor's work (funded and not yet released). */
export function heldMinor(milestones: readonly M[]): bigint {
  return milestones.filter((m) => HELD.has(m.status)).reduce((sum, m) => sum + BigInt(m.amount_minor), 0n);
}

/** NGN already released from escrow for this contractor's work. */
export function releasedMinor(milestones: readonly M[]): bigint {
  return milestones
    .filter((m) => m.status === "released")
    .reduce((sum, m) => sum + BigInt(m.amount_minor), 0n);
}

/** The milestone being worked on: the first one not yet released. */
export function currentMilestone<T extends M>(milestones: readonly T[]): T | undefined {
  return [...milestones].sort((a, b) => a.sequence - b.sequence).find((m) => m.status !== "released");
}

/** What the contractor needs to act on: milestones sent back for rework. */
export function needsContractor<T extends M>(milestones: readonly T[]): T[] {
  return milestones.filter(isSentBack);
}
