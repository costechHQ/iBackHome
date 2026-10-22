// The six set-up steps of a project (WEB-CLIENT-003 CS-05), worked out from the project, its BoQ approvals and
// its milestones. Pure, so the list, the tracker and the tests share it. Contractor invitations can't be read
// (MX-02), so "contractor joined" means a contractor is on the project.

export type SetupKey = "created" | "contractor" | "site" | "supervisor" | "boq" | "funded";

export type SetupStep = { key: SetupKey; label: string; done: boolean };

type Project = {
  status: string;
  contractor_id?: string | null;
  supervisor_id?: string | null;
  site?: unknown | null;
};

type Boq = { approvals_missing: readonly string[] } | null | undefined;

const APPROVED = new Set(["active", "paused", "completed"]);

export function setupSteps(
  project: Project,
  boq: Boq,
  milestones: readonly { status: string }[] = [],
): SetupStep[] {
  const approved = APPROVED.has(project.status);
  return [
    { key: "created", label: "Project created", done: true },
    { key: "contractor", label: "Contractor added", done: Boolean(project.contractor_id) },
    { key: "site", label: "Site pinned", done: Boolean(project.site) },
    { key: "supervisor", label: "Supervisor assigned", done: Boolean(project.supervisor_id) },
    {
      key: "boq",
      label: "BoQ approved",
      done: approved || (project.status === "boq_review" && (boq?.approvals_missing.length ?? 1) === 0),
    },
    { key: "funded", label: "First milestone funded", done: milestones.some((m) => m.status !== "pending") },
  ];
}

export type NextAction =
  | { kind: "site"; label: string }
  | { kind: "review_boq"; label: string }
  | { kind: "wait"; label: string }
  | { kind: "fund"; label: string }
  | null;

/** What the client should do next, in the design's words. */
export function nextAction(
  project: Project,
  boq: Boq,
  milestones: readonly { status: string }[] = [],
): NextAction {
  if (!project.site) return { kind: "site", label: "Pin your site and draw its boundary" };
  if (project.status === "draft") return { kind: "wait", label: "Waiting for your contractor's BoQ" };
  if (project.status === "boq_review") {
    if (boq?.approvals_missing.includes("client") ?? true)
      return { kind: "review_boq", label: "Review the BoQ" };
    return { kind: "wait", label: "Waiting for the other approvals" };
  }
  if (APPROVED.has(project.status) && !milestones.some((m) => m.status !== "pending"))
    return { kind: "fund", label: "Fund the first milestone" };
  return null;
}

export function doneCount(steps: readonly SetupStep[]): number {
  return steps.filter((s) => s.done).length;
}
