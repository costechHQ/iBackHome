"use client";

import { Camera, Check, Hand, Lock, Scale } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { milestoneActions } from "@/common/actions";
import { ApiError } from "@/common/api/errors";
import { useEvidence, useMilestones, useProject, type Milestone } from "@/common/api/queries";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDate } from "@/common/time";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ConfirmDialog } from "@/common/ui/dialog";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";

import { conflictCopy } from "./conflict";
import { currentMilestone, isSentBack } from "./contractor";
import { useClaim } from "./writes";

// WEB-CONTRACTOR-005 Milestones and claim (NGN only, WAT). The milestone being worked on opens up: what the
// supervisor has captured for it, and "Claim milestone" when it's funded. The designed evidence rows are ops
// checklist templates the API doesn't serve yet (PACKAGE-REPORT W-10), so the row lists the supervisor's
// captures. Supplier deductions (MX-05) and the supervisor card (MX-26) aren't shown yet.

function Node({ m }: { m: Milestone }) {
  const base = "flex size-9 flex-none items-center justify-center rounded-pill";
  if (m.status === "released" || m.status === "approved")
    return (
      <span className={cn(base, "bg-navy-900 text-white")}>
        <Check aria-hidden strokeWidth={2.5} className="size-4" />
      </span>
    );
  if (m.status === "claimed" || m.status === "verified")
    return (
      <span className={cn(base, "border-2 border-warn-fg text-warn-fg")}>
        <Hand aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  if (m.status === "disputed")
    return (
      <span className={cn(base, "border-2 border-bad-fg text-bad-fg")}>
        <Scale aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  if (m.status === "funded")
    return (
      <span className={cn(base, "border-2 border-navy-900 text-navy-900")}>
        <Lock aria-hidden strokeWidth={2} className="size-4" />
      </span>
    );
  return (
    <span className={cn(base, "type-small border border-dashed border-line-strong text-slate")}>
      {m.sequence}
    </span>
  );
}

/** The chip a contractor sees; a claim sent back reads "Funded · rework needed" (state-to-ui.md). */
export function ContractorChip({ m }: { m: Milestone }) {
  if (isSentBack(m)) return <ToneChip label="Funded · rework needed" tone="neutral" size="small" />;
  return <StatusChip entity="milestone" state={m.status} audience="contractor" size="small" />;
}

function subline(m: Milestone, timeZone: string) {
  if (m.released_at) return `Released ${formatDate(m.released_at, timeZone)}`;
  if (isSentBack(m)) return "Sent back by the supervisor · fix it, then claim again";
  if (m.status === "claimed") return "Waiting for the supervisor";
  if (m.status === "verified") return "Verified · waiting for the client's approval";
  if (m.status === "approved") return "Approved · the escrow partner is releasing it";
  if (m.status === "disputed") return "Release paused · under review by iBackHome";
  if (m.funded_at) return `Funded ${formatDate(m.funded_at, timeZone)}`;
  return "Not funded yet. You can start once the client funds it.";
}

function Captures({ projectId, milestone }: { projectId: string; milestone: Milestone }) {
  const timeZone = useViewerTimeZone();
  const supervisor = useEvidence(projectId, { milestone_id: milestone.id, captured_by_role: "supervisor" });
  const mine = useEvidence(projectId, { milestone_id: milestone.id, captured_by_role: "contractor" });
  const items = supervisor.data ?? [];
  return (
    <div className="overflow-hidden rounded-card border border-line bg-white">
      <div className="flex items-center justify-between border-b border-line px-4 py-3">
        <p className="type-small font-semibold text-ink">Evidence · captured by the supervisor on site</p>
        <p className="type-small text-slate">{items.length} captured</p>
      </div>
      {items.length ? (
        <ul>
          {items.map((e) => (
            <li
              key={e.id}
              className="flex items-center gap-3 border-b border-line px-4 py-2.5 last:border-b-0"
            >
              <Camera aria-hidden strokeWidth={1.75} className="size-4 text-slate" />
              <span className="type-small flex-1 text-ink">{formatDate(e.captured_at, timeZone)}</span>
              <ToneChip
                label={e.status === "accepted" ? "Accepted" : "Checking"}
                tone={e.status === "accepted" ? "ok" : "neutral"}
                size="small"
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="type-small px-4 py-3 text-slate">
          The supervisor captures the evidence on site after you claim.
        </p>
      )}
      {mine.data?.length ? (
        <p className="type-small border-t border-line px-4 py-3 text-slate">
          Your own photos ({mine.data.length} uploaded) are shared with the client but don&apos;t count toward
          verification.
        </p>
      ) : null}
    </div>
  );
}

export function ContractorMilestones({ projectId }: { projectId: string }) {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const claim = useClaim(projectId);
  const [claiming, setClaiming] = useState<Milestone | null>(null);

  if (project.isPending || milestones.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the milestones">
          <Skeleton className="h-20 w-full" />
          <Skeleton className="h-40 w-full" />
        </Loading>
      </div>
    );
  }
  if (!project.data || !milestones.data) return <ServerErrorContent reference={null} />;

  const ordered = [...milestones.data].sort((a, b) => a.sequence - b.sequence);
  const current = currentMilestone(ordered);
  const conflict =
    claim.error instanceof ApiError && claim.error.status === 409 ? (claiming ?? current) : null;

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        {conflict ? (
          <div role="alert" className="rounded-card border-l-4 border-warn-fg bg-warn-bg p-4">
            <p className="font-semibold text-ink">{conflictCopy(conflict.name, conflict.status).title}</p>
            <p className="type-small text-slate">Nothing was sent twice. The list shows where it is now.</p>
          </div>
        ) : null}
        <Card className="overflow-hidden">
          <ol>
            {ordered.map((m) => {
              const open = m.id === current?.id;
              const actions = milestoneActions(m, project.data, viewer, { online });
              return (
                <li
                  key={m.id}
                  className={cn("border-b border-line last:border-b-0", open && "bg-row-highlight")}
                >
                  <div className="flex items-center gap-4 px-5 py-4">
                    <Node m={m} />
                    <div className="flex flex-1 flex-col gap-1">
                      <p className="flex flex-wrap items-center gap-2">
                        <span className="type-h3 text-ink">{m.name}</span>
                        <ContractorChip m={m} />
                      </p>
                      <p className="type-small text-slate">{subline(m, timeZone)}</p>
                    </div>
                    <span className="ibh-tabular font-semibold text-ink">
                      {formatMoney(m.amount_minor, "NGN")}
                    </span>
                  </div>
                  {open && m.status !== "pending" ? (
                    <div className="flex flex-col gap-4 px-5 pb-5 sm:pl-18">
                      <Captures projectId={projectId} milestone={m} />
                      {isSentBack(m) ? (
                        <Button asChild size="lg" className="self-start">
                          <Link href={`/c/projects/${projectId}/milestones/${m.id}`}>See what to fix</Link>
                        </Button>
                      ) : actions.has("claim") ? (
                        <div className="flex flex-wrap items-center gap-4">
                          <Button size="lg" onClick={() => setClaiming(m)}>
                            Claim milestone
                          </Button>
                          <p className="type-small text-slate">Claim only when every item is finished.</p>
                        </div>
                      ) : null}
                    </div>
                  ) : null}
                </li>
              );
            })}
          </ol>
        </Card>
      </div>

      {current && current.status !== "pending" ? (
        <aside className="flex flex-col gap-6">
          <Card className="flex flex-col gap-3 p-5">
            <CardLabel>{current.name} money</CardLabel>
            <dl className="flex flex-col gap-2">
              <div className="flex justify-between gap-4">
                <dt className="text-slate">Held in escrow</dt>
                <dd className="ibh-tabular font-semibold text-ink">
                  {formatMoney(current.amount_minor, "NGN")}
                </dd>
              </div>
              <div className="flex justify-between gap-4 border-t border-line pt-2">
                <dt className="text-slate">For you on release</dt>
                <dd className="ibh-tabular font-semibold text-ink">
                  {formatMoney(current.amount_minor, "NGN")}
                </dd>
              </div>
            </dl>
            <p className="type-small text-slate">
              Paid after the supervisor verifies and the client approves. {ESCROW_LINE}
            </p>
          </Card>
        </aside>
      ) : null}

      <ConfirmDialog
        open={claiming !== null}
        onOpenChange={(open) => !claim.isPending && !open && setClaiming(null)}
        busy={claim.isPending}
        title={`Claim ${claiming?.name ?? ""} as finished?`}
        description="The supervisor visits to check it. If any item isn't ready, they send the claim back with reasons and you claim again after fixing it."
        confirmLabel="Claim milestone"
        onConfirm={() => {
          if (!claiming) return;
          claim.mutate(claiming.id, { onSettled: () => setClaiming(null) });
        }}
      />
    </div>
  );
}
