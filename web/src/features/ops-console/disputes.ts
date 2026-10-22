// What the dispute screens (WEB-OPS-006) need to know, pure so the screens and tests share it. Resolution
// takes two different ops people choosing the same outcome, for release and for rework alike (the backend
// decides; the design's "rework needs one decision" is PACKAGE-REPORT B-3).

import { ApiError } from "@/common/api/errors";
import type { Tone } from "@/common/status";

type Proposal = { proposed_outcome?: string | null; proposed_by?: string | null };

export type Outcome = "release" | "rework";

export type Stage = "needs_proposal" | "awaiting_other" | "needs_second";

/** Where a dispute is for this ops person: nobody has proposed, they proposed, or someone else did. */
export function stageFor(d: Proposal, viewerId: string): Stage {
  if (!d.proposed_by) return "needs_proposal";
  return d.proposed_by === viewerId ? "awaiting_other" : "needs_second";
}

/** The queue's status chip (state-to-ui.md: "Waiting for 2nd approver" after a proposal). */
export function queueChip(d: Proposal): { label: string; tone: Tone } {
  return d.proposed_by
    ? { label: "Waiting for 2nd approver", tone: "warn" }
    : { label: "Waiting for a proposal", tone: "neutral" };
}

export function outcomeOf(value: string | null | undefined): Outcome | null {
  return value === "release" || value === "rework" ? value : null;
}

export const OUTCOME_LABEL: Record<Outcome, string> = { release: "Release", rework: "Rework" };

/** A 409 from resolve is a designed state: who may act next, or the dispute moved on. */
export function resolveConflict(error: unknown): { title: string; body: string } | null {
  if (!(error instanceof ApiError) || error.status !== 409) return null;
  if (error.code === "second_approval_required")
    return {
      title: "You proposed this resolution",
      body: "A different ops person must confirm it. Nobody can approve their own proposal.",
    };
  if (error.code === "resolution_mismatch")
    return {
      title: "That isn't the proposed outcome",
      body: "Both approvals must choose the same outcome. The proposal is shown above as it is now.",
    };
  if (error.code === "dispute_not_open")
    return {
      title: "This dispute is already resolved",
      body: "Nothing changed. The queue shows what's open now.",
    };
  return { title: "This dispute changed", body: "Nothing changed. The page shows where it is now." };
}

type AuditEntry = {
  id: string;
  action: string;
  actor_id?: string | null;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  at: string;
};

export type TimelineItem = { id: string; at: string; text: string; quote: string | null; byViewer: boolean };

function text(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

/** The dispute's timeline from the audit log: the milestone's steps and the dispute's, oldest first. */
export function timeline(
  entries: readonly AuditEntry[],
  milestoneName: string,
  viewerId: string,
): TimelineItem[] {
  const items: TimelineItem[] = [];
  for (const e of entries) {
    const before = e.before ?? {};
    const after = e.after ?? {};
    let line: string | null = null;
    let quote: string | null = null;
    switch (e.action) {
      case "milestone.funded":
        line =
          before.status === "claimed"
            ? `The supervisor sent ${milestoneName} back`
            : before.status === "disputed"
              ? `${milestoneName} went back to Funded for rework`
              : `${milestoneName} was funded`;
        break;
      case "milestone.claimed":
        line = `The contractor claimed ${milestoneName}`;
        break;
      case "milestone.verified":
        line = `The supervisor verified ${milestoneName}`;
        break;
      case "milestone.approved":
        line = `${milestoneName} was approved for release`;
        break;
      case "milestone.disputed":
        line = `Release of ${milestoneName} paused by the dispute`;
        break;
      case "milestone.released":
        line = `${milestoneName} was released`;
        break;
      case "dispute.opened":
        line = "The client raised the dispute";
        quote = text(after.reason);
        break;
      case "dispute.resolution_proposed": {
        const outcome = outcomeOf(text(after.proposed_outcome));
        line = `Proposed: ${outcome ? OUTCOME_LABEL[outcome].toLowerCase() : "a resolution"}`;
        quote = text(after.resolution_notes);
        break;
      }
      case "dispute.resolved":
        line = after.status === "resolved_release" ? "Resolved: release" : "Resolved: rework";
        break;
      default:
        line = null;
    }
    if (line) items.push({ id: e.id, at: e.at, text: line, quote, byViewer: e.actor_id === viewerId });
  }
  return items.sort((a, b) => a.at.localeCompare(b.at));
}

/** The first ops person's note, from their proposal in the audit log. */
export function proposalNote(entries: readonly AuditEntry[]): string | null {
  const proposal = [...entries].reverse().find((e) => e.action === "dispute.resolution_proposed");
  return proposal ? text(proposal.after?.resolution_notes) : null;
}

/** A dispute's display reference (the backend has none yet): D- and the start of its id. */
export function disputeRef(id: string): string {
  return `D-${id.slice(0, 8)}`;
}
