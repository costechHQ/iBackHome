"use client";

import { useQueries } from "@tanstack/react-query";
import { House, RotateCcw } from "lucide-react";
import Link from "next/link";

import { api, call } from "@/common/api/client";
import { mockPayouts } from "@/common/api/mocks";
import { useMock } from "@/common/api/mocks/context";
import { keys, useProjects, type Milestone } from "@/common/api/queries";
import { useViewer } from "@/common/auth/viewer";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDate } from "@/common/time";
import { Button } from "@/common/ui/button";
import { EscrowTrustLine } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";
import {
  currentMilestone,
  heldMinor,
  needsContractor,
  notReady,
  releasedMinor,
} from "@/features/milestones/contractor";

// WEB-CONTRACTOR-003 Projects dashboard. NGN only, WAT. What needs the contractor (milestones sent back for
// rework), then one card per project. "Paid to you" needs payout history (MX-06): the mock where it's on, else
// hidden. Names (MX-26), the BoQ item (a later stage) and the track record (MX-23) aren't shown yet.

function greeting(timeZone: string, name: string | null) {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", hourCycle: "h23" }).format(new Date()),
  );
  const part = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${part}, ${name.split(/\s+/)[0]}` : part;
}

const WORK: Record<string, string> = {
  pending: "not funded yet",
  funded: "funded, work can start",
  claimed: "waiting for the supervisor",
  verified: "verified, waiting for the client",
  approved: "being released",
  disputed: "release paused",
};

function PaidToYou() {
  const on = useMock("MX-06");
  if (!on) return null;
  const payouts = mockPayouts();
  const total = payouts.items.reduce((sum, p) => sum + BigInt(p.amountMinor), 0n);
  const last = payouts.items[0];
  return (
    <Card className="flex flex-col gap-3 p-5">
      <CardLabel>Paid to you</CardLabel>
      <p className="ibh-tabular type-h2 text-ink">{formatMoney(total, "NGN")}</p>
      <p className="type-small text-slate">
        {payouts.items.length} payouts to {payouts.bankName} {payouts.accountMasked}.
        {last ? ` Last on ${formatDate(last.completedAt, "Africa/Lagos")}.` : ""}
      </p>
      <EscrowTrustLine variant="card" />
    </Card>
  );
}

export function ContractorHome() {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const projects = useProjects();
  const milestoneQueries = useQueries({
    queries: (projects.data?.items ?? []).map((p) => ({
      queryKey: keys.milestones(p.id),
      queryFn: () =>
        call(
          api().GET("/api/v1/projects/{project_id}/milestones", { params: { path: { project_id: p.id } } }),
        ),
    })),
  });

  if (projects.isPending || milestoneQueries.some((q) => q.isPending)) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-10">
        <Loading label="Loading your projects">
          <Skeleton className="h-9 w-80" />
          <Skeleton className="h-40 w-full" />
        </Loading>
      </div>
    );
  }
  if (projects.error) return <ServerErrorContent reference={null} onRetry={() => void projects.refetch()} />;

  const items = (projects.data?.items ?? []).map((p, i) => ({
    project: p,
    milestones: (milestoneQueries[i]?.data ?? []) as Milestone[],
  }));
  const needs = items.flatMap(({ project, milestones }) =>
    needsContractor(milestones).map((m) => ({ project, milestone: m })),
  );

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 sm:px-10 lg:grid-cols-3">
      <div className="flex flex-col gap-6 lg:col-span-2">
        <h1 className="type-h1 text-ink">{greeting(timeZone, viewer.fullName)}</h1>

        {needs.length ? (
          <Card className="overflow-hidden">
            <h2 className="border-b border-line px-5 py-4 font-semibold text-ink">
              Needs you · {needs.length}
            </h2>
            <ul>
              {needs.map(({ project, milestone }) => {
                const count = notReady(milestone);
                return (
                  <li
                    key={milestone.id}
                    className="flex flex-wrap items-center gap-4 border-b border-line px-5 py-4 last:border-b-0"
                  >
                    <span className="flex size-10 flex-none items-center justify-center rounded-control bg-mist">
                      <RotateCcw aria-hidden strokeWidth={1.75} className="size-5 text-navy-900" />
                    </span>
                    <div className="flex min-w-0 flex-1 flex-col gap-1">
                      <p className="flex flex-wrap items-center gap-2">
                        <span className="font-semibold text-ink">{milestone.name} needs rework</span>
                        {milestone.latest_verification ? (
                          <ToneChip
                            label={`Sent back ${formatDate(milestone.latest_verification.created_at, timeZone)}`}
                            tone="warn"
                            size="small"
                          />
                        ) : null}
                      </p>
                      <p className="type-small text-slate">
                        {count
                          ? `The supervisor found ${count.notReady} of ${count.total} checklist items not ready. `
                          : "The supervisor sent your claim back. "}
                        Fix them, then claim again. {project.title}.
                      </p>
                    </div>
                    <Button asChild>
                      <Link href={`/c/projects/${project.id}/milestones/${milestone.id}`}>
                        See what to fix
                      </Link>
                    </Button>
                  </li>
                );
              })}
            </ul>
          </Card>
        ) : null}

        <ul className="grid gap-6 sm:grid-cols-2">
          {items.map(({ project, milestones }) => {
            const released = milestones.filter((m) => m.status === "released").length;
            const current = currentMilestone(milestones);
            return (
              <li key={project.id}>
                <Link
                  href={`/c/projects/${project.id}/milestones`}
                  className="block h-full rounded-card hover:shadow-raised"
                >
                  <Card className="flex h-full flex-col gap-3 p-5">
                    <div className="flex h-24 items-center justify-center rounded-control bg-placeholder text-slate">
                      <House aria-hidden strokeWidth={1.75} className="size-6" />
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <h2 className="type-h3 text-ink">{project.title}</h2>
                      <StatusChip
                        entity="project"
                        state={project.status}
                        audience="contractor"
                        size="small"
                      />
                    </div>
                    <p className="type-small text-slate">{project.address}</p>
                    {milestones.length ? (
                      <div
                        role="progressbar"
                        aria-label={`${released} of ${milestones.length} milestones released`}
                        aria-valuemin={0}
                        aria-valuemax={milestones.length}
                        aria-valuenow={released}
                        className="h-2 overflow-hidden rounded-pill bg-line"
                      >
                        <div
                          className="h-full bg-navy-900"
                          style={{ width: `${Math.round((released / milestones.length) * 100)}%` }}
                        />
                      </div>
                    ) : null}
                    <p className="text-ink">
                      {released} of {milestones.length} milestones released
                      {current
                        ? ` · ${current.name}: ${current.status === "funded" && current.latest_verification?.decision === "rejected" ? "rework" : (WORK[current.status] ?? current.status)}`
                        : ""}
                    </p>
                    <p className="ibh-tabular type-small text-accent">
                      {formatMoney(releasedMinor(milestones), "NGN")} released ·{" "}
                      {formatMoney(heldMinor(milestones), "NGN")} waiting in escrow
                    </p>
                  </Card>
                </Link>
              </li>
            );
          })}
        </ul>
      </div>

      <aside className="flex flex-col gap-6">
        <PaidToYou />
        <Card className="flex flex-col gap-2 p-5">
          <CardLabel>On site</CardLabel>
          <p className="type-small text-slate">
            Use the iBackHome app to claim milestones and take contractor photos on site.
          </p>
        </Card>
      </aside>
    </div>
  );
}
