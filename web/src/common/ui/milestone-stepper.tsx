import { Check, Hand, Lock, Scale } from "lucide-react";

import { formatDate } from "../time";
import { cn } from "./cn";

// Milestone stepper (components.md, Milestones and evidence; WEB-CLIENT-013): Funded, Claimed, Verified,
// Approved (or Disputed), Released. Done steps are navy with a check; the current step is a ring whose icon says
// what it is (lock = funded, hand = claimed, check = verified, scales = disputed); later steps are dashed with
// their number. Each node differs by icon and label, never by colour alone.

export type StepperMilestone = {
  status: string;
  funded_at: string | null;
  claimed_at: string | null;
  verified_at: string | null;
  approved_at: string | null;
  released_at: string | null;
};

type Step = { key: string; label: string; at: string | null };

function steps(m: StepperMilestone, disputedAt: string | null): Step[] {
  return [
    { key: "funded", label: "Funded", at: m.funded_at },
    { key: "claimed", label: "Claimed", at: m.claimed_at },
    { key: "verified", label: "Verified", at: m.verified_at },
    m.status === "disputed"
      ? { key: "disputed", label: "Disputed", at: disputedAt }
      : { key: "approved", label: "Approved", at: m.approved_at },
    { key: "released", label: "Released", at: m.released_at },
  ];
}

// Which step the milestone is on (-1: none yet). Approved and released show as done.
const CURRENT: Record<string, number> = {
  pending: -1,
  funded: 0,
  claimed: 1,
  verified: 2,
  disputed: 3,
  approved: 3,
  released: 4,
};

function Node({
  kind,
  index,
}: {
  kind: "done" | "funded" | "claimed" | "verified" | "disputed" | "todo";
  index: number;
}) {
  const base = "flex size-7 flex-none items-center justify-center rounded-pill";
  switch (kind) {
    case "done":
      return (
        <span className={cn(base, "bg-navy-900 text-white")}>
          <Check aria-hidden strokeWidth={2.5} className="size-4" />
        </span>
      );
    case "funded":
      return (
        <span className={cn(base, "border-2 border-accent bg-white text-accent")}>
          <Lock aria-hidden strokeWidth={2} className="size-3.5" />
        </span>
      );
    case "claimed":
      return (
        <span className={cn(base, "border-2 border-warn-fg bg-white text-warn-fg")}>
          <Hand aria-hidden strokeWidth={2} className="size-3.5" />
        </span>
      );
    case "verified":
      return (
        <span className={cn(base, "border-2 border-accent bg-white text-accent")}>
          <Check aria-hidden strokeWidth={2.5} className="size-4" />
        </span>
      );
    case "disputed":
      return (
        <span className={cn(base, "border-2 border-bad-fg bg-white text-bad-fg")}>
          <Scale aria-hidden strokeWidth={2} className="size-3.5" />
        </span>
      );
    default:
      return (
        <span
          className={cn(
            base,
            "type-caption border border-dashed border-line-strong bg-white tracking-normal text-slate",
          )}
        >
          {index + 1}
        </span>
      );
  }
}

export function MilestoneStepper({
  milestone,
  timeZone,
  disputedAt = null,
  className,
}: {
  milestone: StepperMilestone;
  timeZone: string;
  disputedAt?: string | null;
  className?: string;
}) {
  const list = steps(milestone, disputedAt);
  const current = CURRENT[milestone.status] ?? -1;
  const finished = milestone.status === "approved" || milestone.status === "released";
  const day = (iso: string) => formatDate(iso, timeZone).split(" ").slice(1).join(" "); // "30 Nov"

  return (
    <ol
      aria-label="Milestone progress"
      className={cn(
        "grid grid-cols-5 gap-1 rounded-card border border-line bg-white p-4 sm:gap-2 sm:p-5",
        className,
      )}
    >
      {list.map((step, i) => {
        const done = i < current || (finished && i <= current);
        const kind = done
          ? "done"
          : i === current
            ? (step.key as "funded" | "claimed" | "verified" | "disputed")
            : "todo";
        const state = done ? "done" : i === current ? "current" : "not yet";
        return (
          <li
            key={step.key}
            aria-current={i === current ? "step" : undefined}
            className="relative flex flex-col gap-2"
          >
            {i < list.length - 1 ? (
              <span
                aria-hidden
                className={cn(
                  "absolute top-3.5 right-0 left-9 h-0.5",
                  i < current ? "bg-navy-900" : "bg-line",
                )}
              />
            ) : null}
            <Node kind={kind} index={i} />
            {/* The type styles can't take breakpoints (theme.css), so phones get the caption-size label. */}
            <span className="font-semibold text-ink">
              <span className="type-caption tracking-normal sm:hidden">{step.label}</span>
              <span className="type-small max-sm:hidden">{step.label}</span>
              <span className="sr-only">, {state}</span>
            </span>
            {/* Phones show the labels only (WEB-CLIENT-013 mobile). */}
            <span className="type-caption tracking-normal text-muted max-sm:hidden">
              {step.at ? day(step.at) : "—"}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
