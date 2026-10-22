"use client";

import { Check, Clock } from "lucide-react";
import Link from "next/link";

import { useMilestones, useProject, type Milestone } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { fromGeoJson } from "@/common/map/geo";
import { formatMoney } from "@/common/money";
import { formatDate } from "@/common/time";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";

import { useBoq } from "./api";
import { setupSteps, type SetupKey } from "./setup";

// WEB-CLIENT-003 CS-05 set-up tracker at /projects/:id/setup. People are named by role until MX-26; an
// invitation's accepted / declined state needs MX-02, so "Contractor added" says only that they are on the
// project. "Fund the first milestone" opens its funding page (WEB-CLIENT-007).

const ROLE_NAMES: Record<string, string> = { client: "you", contractor: "your contractor", ops: "our team" };

export function SetupTracker({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const boq = useBoq(projectId);

  if (project.isPending || milestones.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the set-up">
          <Skeleton className="h-72 w-full" />
        </Loading>
      </div>
    );
  }
  if (!project.data) return <ServerErrorContent reference={null} onRetry={() => void project.refetch()} />;
  const p = project.data;
  const ms = (milestones.data ?? []) as Milestone[];
  const steps = setupSteps(p, boq.data, ms);
  const firstOpen = steps.find((s) => !s.done)?.key;
  const corners = p.site ? fromGeoJson(p.site.geofence).length : 0;
  const editable = p.status === "draft" || p.status === "boq_review";
  const approved = boq.data?.approvals.map((a) => ROLE_NAMES[a.role] ?? a.role) ?? [];
  const missing = boq.data?.approvals_missing ?? [];

  const detail: Record<SetupKey, string> = {
    created: `${formatDate(p.created_at, timeZone)} · budget ${formatMoney(p.budget_minor, p.currency)}`,
    contractor: p.contractor_id ? "On the project" : "Not added",
    site: p.site
      ? `Boundary saved · ${corners} corners${editable ? " · you can change it until approval" : " · locked"}`
      : "Pin your plot and draw its boundary",
    supervisor: p.supervisor_id
      ? "A vetted supervisor · assigned by iBackHome"
      : "We assign a vetted supervisor near your site",
    boq:
      p.status === "draft"
        ? "Waiting for your contractor to price the work"
        : p.status === "boq_review"
          ? missing.includes("client")
            ? `${approved.length ? `${capitalise(approved.join(" and "))} approved · ` : ""}waiting for you`
            : `Waiting for ${missing.map((r) => ROLE_NAMES[r] ?? r).join(" and ")}`
          : "Approved by you, your contractor and our team",
    funded: steps[4]!.done ? "Opens now" : "Opens once all three have approved",
  };

  const firstPending = [...ms].sort((a, b) => a.sequence - b.sequence).find((x) => x.status === "pending");
  const action: Partial<Record<SetupKey, React.ReactNode>> = {
    funded:
      steps[4]!.done && !steps[5]!.done && firstPending ? (
        <Button asChild>
          <Link href={`/projects/${p.id}/fund/${firstPending.id}`}>Fund {firstPending.name}</Link>
        </Button>
      ) : null,
    site: (
      <Button asChild variant={p.site ? "outline" : "primary"}>
        <Link href={`/projects/${p.id}/site`}>{p.site ? "View map" : "Pin your site"}</Link>
      </Button>
    ),
    boq:
      p.status === "boq_review" || steps[4]!.done ? (
        <Button asChild variant={missing.includes("client") ? "primary" : "outline"}>
          <Link href={`/projects/${p.id}/boq`}>{missing.includes("client") ? "Review BoQ" : "View BoQ"}</Link>
        </Button>
      ) : null,
  };

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <h2 className="sr-only">Set-up</h2>
      <Card className="overflow-hidden lg:col-span-2">
        <ol>
          {steps.map((s, i) => {
            const current = s.key === firstOpen;
            return (
              <li
                key={s.key}
                aria-current={current ? "step" : undefined}
                className={cn(
                  "flex flex-wrap items-center gap-4 border-b border-line px-5 py-4 last:border-b-0",
                  current && "bg-row-highlight",
                )}
              >
                <span
                  className={cn(
                    "type-small flex size-8 flex-none items-center justify-center rounded-pill font-semibold",
                    s.done
                      ? "bg-navy-900 text-white"
                      : current
                        ? "border-2 border-accent text-accent"
                        : "border border-dashed border-line-strong text-slate",
                  )}
                >
                  {s.done ? <Check aria-hidden strokeWidth={2.5} className="size-4" /> : i + 1}
                  <span className="sr-only">{s.done ? " (done)" : ""}</span>
                </span>
                <div className="flex flex-1 flex-col gap-0.5">
                  <p className="font-semibold text-ink">{s.label}</p>
                  <p className="type-small text-slate">{detail[s.key]}</p>
                </div>
                {action[s.key] ?? null}
              </li>
            );
          })}
        </ol>
      </Card>
      <aside className="flex flex-col gap-4">
        {p.supervisor_id ? (
          <Card className="flex flex-col gap-2 p-5">
            <CardLabel>Your supervisor</CardLabel>
            <p className="flex items-center gap-2 font-semibold text-ink">
              Assigned <ToneChip label="Vetted" tone="ok" size="small" />
            </p>
            <p className="type-small text-slate">
              Assigned by iBackHome. Supervisors rotate after two consecutive milestones, and others make
              unannounced spot checks.
            </p>
          </Card>
        ) : (
          <Card className="flex flex-col gap-2 border-dashed p-5">
            <CardLabel>Before assignment</CardLabel>
            <p className="flex items-start gap-3">
              <Clock aria-hidden strokeWidth={1.75} className="mt-0.5 size-5 flex-none text-slate" />
              <span>
                <span className="block font-semibold text-ink">Choosing your supervisor</span>
                <span className="type-small text-slate">
                  A vetted builder or engineer near your site, with no family link to your contractor.
                </span>
              </span>
            </p>
          </Card>
        )}
      </aside>
    </div>
  );
}

function capitalise(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1);
}
