// The contractor's track record on their profile (WEB-CONTRACTOR-009), worked out only from what the platform
// recorded on their own projects. The design's "verified the first time", "average days from claim to
// verification" and "disputes decided against you" need the full verification and dispute history (MX-23),
// so they aren't computed here.

type M = { status: string; latest_verification?: { decision: string } | null };
type P = { status: string };

const VERIFIED = new Set(["verified", "approved", "released", "disputed"]);
const SETTING_UP = new Set(["draft", "boq_review"]);

export function trackRecord(items: readonly { project: P; milestones: readonly M[] }[]) {
  const milestones = items.flatMap((i) => i.milestones);
  return {
    verified: milestones.filter((m) => VERIFIED.has(m.status)).length,
    released: milestones.filter((m) => m.status === "released").length,
    sentBackNow: milestones.filter(
      (m) => m.status === "funded" && m.latest_verification?.decision === "rejected",
    ).length,
    projects: {
      active: items.filter((i) => i.project.status === "active" || i.project.status === "paused").length,
      settingUp: items.filter((i) => SETTING_UP.has(i.project.status)).length,
      completed: items.filter((i) => i.project.status === "completed").length,
    },
  };
}
