// Which actions a viewer may take on a milestone or dispute, from the "Allowed actions by role" column of
// Docs/design/04-api-mapping/state-to-ui.md, narrowed by what the backend enforces. Anything not returned is
// hidden in the UI. This is presentation only: the backend checks every one of these rules again.

import type { Audience } from "./status";

export type Viewer = { id: string; role: Audience };

export type ProjectContext = {
  status: string;
  client_id: string;
  contractor_id: string | null;
  supervisor_id: string | null;
};

export type MilestoneAction =
  | "fund"
  | "claim"
  | "request_materials"
  | "upload_contractor_evidence"
  | "verify"
  | "send_back"
  | "approve"
  | "raise_dispute"
  | "view_dispute"
  | "view_receipt"
  | "see_payout";

// Actions that write, so they need the network (offline: "Approvals and payments are paused").
const WRITES: ReadonlySet<MilestoneAction> = new Set([
  "fund",
  "claim",
  "request_materials",
  "upload_contractor_evidence",
  "verify",
  "send_back",
  "approve",
  "raise_dispute",
]);

// Paused: "Claims, captures and approvals disabled". Completed: read-only.
const BLOCKED_WHEN_PAUSED: ReadonlySet<MilestoneAction> = new Set([
  "claim",
  "upload_contractor_evidence",
  "verify",
  "send_back",
  "approve",
  "raise_dispute",
  "request_materials",
]);

function partyRole(viewer: Viewer, project: ProjectContext): Audience | null {
  if (viewer.role === "ops") return "ops";
  if (viewer.role === "client" && viewer.id === project.client_id) return "client";
  if (viewer.role === "contractor" && viewer.id === project.contractor_id) return "contractor";
  if (viewer.role === "supervisor" && viewer.id === project.supervisor_id) return "supervisor";
  return null;
}

// state -> role -> actions (state-to-ui.md, Milestone table).
const MILESTONE: Record<string, Partial<Record<Audience, readonly MilestoneAction[]>>> = {
  pending: { client: ["fund"] },
  funded: { contractor: ["claim", "request_materials"] },
  claimed: { supervisor: ["verify", "send_back"], contractor: ["upload_contractor_evidence"] },
  verified: { client: ["approve", "raise_dispute"] },
  approved: {},
  // Ops resolve disputes through disputeActions(); the parties can only read the dispute.
  disputed: { client: ["view_dispute"], contractor: ["view_dispute"] },
  released: { client: ["view_receipt"], contractor: ["see_payout"] },
};

export function milestoneActions(
  milestone: { status: string },
  project: ProjectContext,
  viewer: Viewer,
  { online = true }: { online?: boolean } = {},
): Set<MilestoneAction> {
  const role = partyRole(viewer, project);
  if (!role) return new Set();
  let actions = [...(MILESTONE[milestone.status]?.[role] ?? [])];

  if (project.status === "completed") actions = actions.filter((a) => !WRITES.has(a));
  if (project.status === "paused") actions = actions.filter((a) => !BLOCKED_WHEN_PAUSED.has(a));
  // Claims need an active project (the backend refuses otherwise).
  if (project.status !== "active") actions = actions.filter((a) => a !== "claim");
  if (!online) actions = actions.filter((a) => !WRITES.has(a));
  return new Set(actions);
}

export type DisputeContext = {
  status: string;
  proposed_outcome: string | null;
  proposed_by: string | null;
};

export type DisputeAction =
  { kind: "propose" } | { kind: "confirm"; outcome: string } | { kind: "waiting_for_second_approver" };

/**
 * Two different ops users resolve a dispute, for either outcome (backend: escrow.resolve_dispute). The first
 * proposes; a second, different ops user confirms the same outcome. The proposer sees only a waiting state.
 */
export function disputeAction(
  dispute: DisputeContext,
  viewer: Viewer,
  { online = true }: { online?: boolean } = {},
): DisputeAction | null {
  if (viewer.role !== "ops" || dispute.status !== "open") return null;
  if (!dispute.proposed_by || !dispute.proposed_outcome) return online ? { kind: "propose" } : null;
  if (dispute.proposed_by === viewer.id) return { kind: "waiting_for_second_approver" };
  return online ? { kind: "confirm", outcome: dispute.proposed_outcome } : null;
}
