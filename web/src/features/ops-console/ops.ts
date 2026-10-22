// The ops console's pure parts (W8a): how long something has waited, what a project needs from ops, and what is
// happening on it now. Shared by the overview (WEB-OPS-002) and the projects list (WEB-OPS-004).

type M = {
  name: string;
  sequence: number;
  status: string;
  latest_verification?: { decision: string } | null;
};
type P = { status: string; supervisor_id?: string | null };

/** "12 min", "5 h", "2 days": how long ago, for queue ages. */
export function waited(iso: string, now: Date = new Date()): string {
  const minutes = Math.max(0, Math.floor((now.getTime() - new Date(iso).getTime()) / 60_000));
  if (minutes < 60) return `${minutes} min`;
  const hours = Math.floor(minutes / 60);
  if (hours < 48) return `${hours} h`;
  return `${Math.floor(hours / 24)} days`;
}

/** The oldest of a queue's timestamps, or null for an empty queue. */
export function oldest(times: readonly string[]): string | null {
  return times.length ? [...times].sort()[0]! : null;
}

export type Flag = { label: string; tone: "warn" | "bad" | "neutral" };

const SETTING_UP = new Set(["draft", "boq_review"]);

/**
 * What a project needs from ops: its BoQ waiting for the ops approval, no supervisor once it's live, a dispute
 * or a claim sent back. `opsApprovalMissing` comes from the BoQ (only read for projects in BoQ review).
 */
export function projectFlags(project: P, milestones: readonly M[], opsApprovalMissing = false): Flag[] {
  const flags: Flag[] = [];
  if (project.status === "boq_review" && opsApprovalMissing) {
    flags.push({ label: "Needs ops approval", tone: "warn" });
  }
  if (!project.supervisor_id && !SETTING_UP.has(project.status) && project.status !== "completed") {
    flags.push({ label: "No supervisor", tone: "bad" });
  }
  if (milestones.some((m) => m.status === "disputed")) flags.push({ label: "Disputed", tone: "bad" });
  if (milestones.some((m) => m.status === "funded" && m.latest_verification?.decision === "rejected")) {
    flags.push({ label: "Sent back", tone: "neutral" });
  }
  return flags;
}

const NOW: Record<string, string> = {
  pending: "not funded",
  funded: "funded",
  claimed: "claimed",
  verified: "verified",
  approved: "approved, releasing",
  disputed: "disputed",
};

/** "Plastering · claimed": the first milestone not yet released; set-up and finished projects say so. */
export function nowText(project: P, milestones: readonly M[]): string {
  if (project.status === "draft") return "Setup · waiting for the BoQ";
  if (project.status === "boq_review") return "Setup · BoQ in review";
  const current = [...milestones]
    .sort((a, b) => a.sequence - b.sequence)
    .find((m) => m.status !== "released");
  if (!current) return milestones.length ? "All milestones released" : "–";
  const rework = current.status === "funded" && current.latest_verification?.decision === "rejected";
  return `${current.name} · ${rework ? "rework" : (NOW[current.status] ?? current.status)}`;
}

/** Status tabs on the projects list: setup covers draft and BoQ review. */
export const PROJECT_TABS = [
  { key: "all", label: "All", match: () => true },
  { key: "active", label: "Active", match: (s: string) => s === "active" },
  { key: "paused", label: "Paused", match: (s: string) => s === "paused" },
  { key: "setup", label: "Setup", match: (s: string) => SETTING_UP.has(s) },
  { key: "completed", label: "Completed", match: (s: string) => s === "completed" },
] as const;

/** "dispute.propose_resolution" -> "dispute", for the object filter's options. */
export function actionGroup(action: string): string {
  return action.split(".")[0] ?? action;
}
