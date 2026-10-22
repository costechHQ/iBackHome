"use client";

import Link from "next/link";
import { useState } from "react";

import { milestoneActions } from "@/common/actions";
import { useMilestones, useProject, shortId } from "@/common/api/queries";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatTime, formatDate } from "@/common/time";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";

import { ContractorChip } from "./contractor-milestones";
import { isSentBack, notReady } from "./contractor";
import { useClaim } from "./writes";

// WEB-CONTRACTOR-006 Sent back: the supervisor's reasons, each checklist item accepted or not ready, and the
// money still held. The checklist items have no note each (only the overall notes). "Start rework" has no
// backend step, so the screen offers "Claim again" (frame 2). "Dispute this rejection" isn't built (C-11, MX-25).

export function SentBack({ projectId, milestoneId }: { projectId: string; milestoneId: string }) {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const claim = useClaim(projectId);
  const [confirming, setConfirming] = useState(false);

  if (project.isPending || milestones.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the milestone">
          <Skeleton className="h-24 w-full" />
        </Loading>
      </div>
    );
  }
  if (!project.data || !milestones.data) return <ServerErrorContent reference={null} />;
  const m = milestones.data.find((x) => x.id === milestoneId);
  if (!m) return <NotFoundContent />;

  const verification = m.latest_verification;
  const count = notReady(m);
  const canClaim = milestoneActions(m, project.data, viewer, { online }).has("claim");
  const list = `/c/projects/${projectId}/milestones`;

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <div className="flex flex-col gap-5 lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="type-h2 text-ink">{m.name}</h2>
          <ContractorChip m={m} />
        </div>

        {isSentBack(m) && verification ? (
          <>
            <section className="flex flex-col gap-2 rounded-card border-l-4 border-warn-fg bg-warn-bg p-5">
              <p className="type-caption text-warn-fg uppercase">Sent back by the supervisor</p>
              <h2 className="type-h3 text-ink">
                {count
                  ? `${count.notReady} of ${count.total} items aren't ready`
                  : "Your claim was sent back"}
              </h2>
              <p className="text-ink">
                The supervisor, {formatDate(verification.created_at, timeZone)},{" "}
                {formatTime(verification.created_at, timeZone)}
                {verification.notes ? `: “${verification.notes}”` : "."}
              </p>
            </section>
            {verification.checklist.length ? (
              <Card className="overflow-hidden">
                <ul>
                  {verification.checklist.map((item) => (
                    <li
                      key={item.item}
                      className="flex items-start gap-4 border-b border-line px-5 py-4 last:border-b-0"
                    >
                      <div className="flex flex-1 flex-col gap-1.5">
                        <p className="font-semibold text-ink">{item.item}</p>
                        <p className="flex flex-wrap gap-2">
                          {(item.evidence_ids ?? []).map((id) => (
                            <span
                              key={id}
                              className="type-mono rounded-tag border border-line bg-mist px-1.5 text-ink"
                            >
                              {shortId(id)}
                            </span>
                          ))}
                        </p>
                      </div>
                      <ToneChip
                        label={item.passed ? "Accepted" : "Not ready"}
                        tone={item.passed ? "ok" : "bad"}
                        size="small"
                      />
                    </li>
                  ))}
                </ul>
              </Card>
            ) : null}
            {canClaim ? (
              <div className="flex flex-wrap items-center gap-4">
                <Button size="lg" onClick={() => setConfirming(true)}>
                  Claim {m.name} again
                </Button>
                <p className="type-small text-slate">
                  Claim again once every item that wasn&apos;t ready is fixed.
                </p>
              </div>
            ) : null}
          </>
        ) : (
          <Card className="flex flex-col gap-3 p-5">
            <p className="text-slate">
              This milestone hasn&apos;t been sent back. Its progress is on the milestones list.
            </p>
            <Button asChild variant="outline" className="self-start">
              <Link href={list}>See the milestones</Link>
            </Button>
          </Card>
        )}
      </div>

      <aside className="flex flex-col gap-6">
        <Card className="flex flex-col gap-2 p-5">
          <CardLabel>Money</CardLabel>
          <p className="ibh-tabular type-h3 text-ink">
            {formatMoney(m.amount_minor, "NGN")} still held for you
          </p>
          <p className="type-small text-slate">Nothing is lost by a rework. {ESCROW_LINE}</p>
        </Card>
        {isSentBack(m) ? (
          <Card className="flex flex-col gap-2 p-5">
            <CardLabel>Who knows</CardLabel>
            <p className="type-small text-slate">
              The client was told the claim was sent back, with the same reasons.
            </p>
          </Card>
        ) : null}
      </aside>

      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => !claim.isPending && setConfirming(open)}
        busy={claim.isPending}
        title={`Claim ${m.name} as finished?`}
        description="The supervisor re-checks the items they sent back and looks over the rest once more. Only their own captures on site count."
        confirmLabel="Claim milestone"
        onConfirm={() => claim.mutate(m.id, { onSettled: () => setConfirming(false) })}
      />
    </div>
  );
}
