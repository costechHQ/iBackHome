"use client";

import { Check, ChevronRight, Hand, Lock, Scale } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";

import { useLedger, useMilestones } from "@/common/api/queries";
import { toUiState } from "@/common/api/errors";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { moneyByMilestone } from "@/common/ledger";
import { formatDate } from "@/common/time";
import { formatMoney } from "@/common/money";
import { cn } from "@/common/ui/cn";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

// The project's milestones for the client. No client list screen is designed (it sits on the project overview,
// WEB-CLIENT-009, a later stage), so this uses the designed milestone rows of WEB-CONTRACTOR-005, with the
// client's amounts. Each row opens WEB-CLIENT-013.

function Node({ status, sequence }: { status: string; sequence: number }) {
  const base = "flex size-9 flex-none items-center justify-center rounded-pill";
  if (status === "released" || status === "approved")
    return (
      <span className={cn(base, "bg-navy-900 text-white")}>
        <Check aria-hidden strokeWidth={2.5} className="size-4" />
      </span>
    );
  if (status === "verified")
    return (
      <span className={cn(base, "border-2 border-accent text-accent")}>
        <Check aria-hidden strokeWidth={2.5} className="size-4" />
      </span>
    );
  if (status === "claimed")
    return (
      <span className={cn(base, "border-2 border-warn-fg text-warn-fg")}>
        <Hand aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  if (status === "disputed")
    return (
      <span className={cn(base, "border-2 border-bad-fg text-bad-fg")}>
        <Scale aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  if (status === "funded")
    return (
      <span className={cn(base, "border-2 border-navy-900 text-navy-900")}>
        <Lock aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  return (
    <span className={cn(base, "type-small border border-dashed border-line-strong text-slate")}>
      {sequence}
    </span>
  );
}

export function MilestoneList({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const milestones = useMilestones(projectId);
  const ledger = useLedger(projectId);
  const money = useMemo(
    () => (milestones.data && ledger.data ? moneyByMilestone(milestones.data, ledger.data.ledger) : null),
    [milestones.data, ledger.data],
  );

  if (milestones.isPending || ledger.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the milestones">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-20 w-full" />
        </Loading>
      </div>
    );
  }
  if (milestones.error || ledger.error || !milestones.data) {
    const state = toUiState(milestones.error ?? ledger.error);
    return <ServerErrorContent reference={state.kind === "server" ? state.requestId : null} />;
  }

  const ordered = [...milestones.data].sort((a, b) => a.sequence - b.sequence);
  const subline = (m: (typeof ordered)[number]) => {
    if (m.released_at) return `Released ${formatDate(m.released_at, timeZone)}`;
    if (m.status === "verified") return "Needs your approval";
    if (m.status === "disputed") return "Release paused · under review by iBackHome";
    if (m.status === "claimed") return "Waiting for the supervisor";
    if (m.funded_at) return `Funded ${formatDate(m.funded_at, timeZone)}`;
    return "Not funded yet";
  };

  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 pb-24 sm:px-10">
      <h1 className="sr-only">Milestones</h1>
      <Card className="overflow-hidden">
        <ol>
          {ordered.map((m) => {
            const payment = money?.get(m.id)?.payment;
            return (
              <li key={m.id} className="border-b border-line last:border-b-0">
                <Link
                  href={`/projects/${projectId}/milestones/${m.id}`}
                  className="flex min-h-target items-center gap-4 px-5 py-4 hover:bg-row-highlight"
                >
                  <Node status={m.status} sequence={m.sequence} />
                  <div className="flex flex-1 flex-col gap-1">
                    <span className="flex flex-wrap items-center gap-2">
                      <span className="type-h3 text-ink">{m.name}</span>
                      <StatusChip entity="milestone" state={m.status} audience="client" size="small" />
                    </span>
                    <span className="type-small text-slate">{subline(m)}</span>
                  </div>
                  <span className="ibh-tabular flex flex-col items-end">
                    <span className="font-semibold text-ink">
                      {payment
                        ? formatMoney(payment.netMinor, payment.currency)
                        : formatMoney(m.amount_minor, "NGN")}
                    </span>
                    {payment ? (
                      <span className="type-small text-slate">{formatMoney(m.amount_minor, "NGN")}</span>
                    ) : null}
                  </span>
                  <ChevronRight aria-hidden strokeWidth={1.75} className="size-5 flex-none text-muted" />
                </Link>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}
