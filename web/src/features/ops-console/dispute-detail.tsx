"use client";

import { Info } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { useEvidence, useMilestones, useProject, shortId } from "@/common/api/queries";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime, zoneLabel } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { EvidenceCard } from "@/common/ui/evidence";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, CardLabel } from "@/common/ui/surfaces";

import {
  disputeRef,
  OUTCOME_LABEL,
  outcomeOf,
  proposalNote,
  resolveConflict,
  stageFor,
  timeline,
  type Outcome,
} from "./disputes";
import { useAudit, useOpsQueue, useResolve, type QueueDispute } from "./queries";

// WEB-OPS-006 frame 2: the timeline (from the audit log), the evidence on the milestone, the money held, and the
// two-step resolution. The first ops person proposes an outcome with a note; a different one confirms the same
// outcome. "Disagree" isn't built: the backend has no way to withdraw a proposal (PACKAGE-REPORT W-22).

const MAX_NOTE = 2000;

function Timeline({ dispute, milestoneName }: { dispute: QueueDispute; milestoneName: string }) {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const milestoneAudit = useAudit("milestone", dispute.milestone_id);
  const disputeAudit = useAudit("dispute", dispute.dispute_id);
  const items = timeline(
    [...(milestoneAudit.data ?? []), ...(disputeAudit.data ?? [])],
    milestoneName,
    viewer.id,
  );
  return (
    <Card className="flex flex-col">
      <h2 className="type-h3 border-b border-line px-4 py-3 text-ink">
        Timeline · {zoneLabel(dispute.opened_at, timeZone)}
      </h2>
      {milestoneAudit.isPending || disputeAudit.isPending ? (
        <div className="p-4">
          <Loading label="Loading the timeline">
            <Skeleton className="h-24 w-full" />
          </Loading>
        </div>
      ) : (
        <ol className="flex flex-col gap-4 p-4">
          {items.map((item) => (
            <li key={item.id} className="flex gap-3">
              <span aria-hidden className="mt-2 size-1.5 flex-none rounded-pill bg-ink" />
              <div className="flex flex-col gap-0.5">
                <p className="type-ops-body text-ink">
                  {item.text}
                  {item.byViewer ? " (you)" : ""}
                  {item.quote ? `: “${item.quote}”` : ""}
                </p>
                <p className="type-small text-slate">{formatDateTime(item.at, timeZone)}</p>
              </div>
            </li>
          ))}
        </ol>
      )}
    </Card>
  );
}

function Evidence({ dispute }: { dispute: QueueDispute }) {
  const timeZone = useViewerTimeZone();
  const [who, setWho] = useState<"supervisor" | "contractor">("supervisor");
  const evidence = useEvidence(dispute.project_id, { milestone_id: dispute.milestone_id });
  const all = evidence.data ?? [];
  const counts = {
    supervisor: all.filter((e) => e.captured_by_role === "supervisor").length,
    contractor: all.filter((e) => e.captured_by_role === "contractor").length,
  };
  const shown = all.filter((e) => e.captured_by_role === who);
  return (
    <Card className="flex flex-col">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="type-h3 text-ink">Evidence</h2>
        <SegmentedControl
          label="Whose evidence"
          value={who}
          onChange={setWho}
          segments={[
            { value: "supervisor", label: "Supervisor", count: counts.supervisor },
            { value: "contractor", label: "Contractor", count: counts.contractor },
          ]}
        />
      </div>
      {evidence.isPending ? (
        <div className="p-4">
          <Loading label="Loading the evidence">
            <Skeleton className="h-32 w-full" />
          </Loading>
        </div>
      ) : shown.length ? (
        <ul className="grid grid-cols-2 gap-3 p-4">
          {shown.map((e) => (
            <li key={e.id}>
              <EvidenceCard
                item={e}
                audience="ops"
                reference={`EV-${shortId(e.id)}`}
                time={formatDateTime(e.captured_at, timeZone)}
              />
            </li>
          ))}
        </ul>
      ) : (
        <p className="type-small p-4 text-slate">
          {who === "supervisor"
            ? "The supervisor hasn't captured evidence for this milestone."
            : "No contractor photos."}
        </p>
      )}
    </Card>
  );
}

function Resolution({
  dispute,
  milestoneName,
  amountMinor,
}: {
  dispute: QueueDispute;
  milestoneName: string;
  amountMinor: number;
}) {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const ids = { note: useId(), help: useId() };
  const audit = useAudit("dispute", dispute.dispute_id);
  const resolve = useResolve(dispute);
  const stage = stageFor(dispute, viewer.id);
  const proposed = outcomeOf(dispute.proposed_outcome);
  const [choice, setChoice] = useState<Outcome>("release");
  const [note, setNote] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const outcome = stage === "needs_second" && proposed ? proposed : choice;
  const conflict = resolveConflict(resolve.error);

  const submit = () => {
    if (!note.trim()) {
      setProblem("Write a note. It goes in the audit log with your decision.");
      return;
    }
    setProblem(null);
    resolve.mutate({ outcome, notes: note.trim() }, { onSuccess: () => setNote("") });
  };

  if (resolve.data?.resolved) {
    const released = resolve.data.dispute.status === "resolved_release";
    return (
      <Alert tone="ok" title={released ? "Resolved: release" : "Resolved: rework"}>
        {released
          ? `The escrow partner has been asked to pay ${formatMoney(amountMinor, "NGN")}. The client and contractor are told.`
          : `${milestoneName} is back to Funded. The money stays held while the contractor fixes it.`}
      </Alert>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {dispute.proposed_by && proposed ? (
        <div className="flex flex-col gap-1.5 rounded-card border border-line p-4">
          <p className="type-caption text-muted uppercase">Step 1 · Proposed</p>
          <p className="type-ops-body text-ink">
            <span className="font-semibold">{OUTCOME_LABEL[proposed]}</span> by{" "}
            {stage === "awaiting_other" ? "you" : "another ops person"}
            {dispute.proposed_at ? `, ${formatDateTime(dispute.proposed_at, timeZone)}` : ""}
          </p>
          {proposalNote(audit.data ?? []) ? (
            <p className="type-ops-body text-slate">“{proposalNote(audit.data ?? [])}”</p>
          ) : null}
        </div>
      ) : null}

      {stage === "awaiting_other" ? (
        <Alert tone="info" title="Waiting for a second approver">
          A different ops person must confirm {OUTCOME_LABEL[proposed ?? "release"].toLowerCase()}. Nobody can
          approve their own proposal.
        </Alert>
      ) : (
        <div className="flex flex-col gap-3 rounded-card border-2 border-navy-900 p-4">
          <p className="type-caption text-muted uppercase">
            {stage === "needs_proposal" ? "Step 1 · Propose" : "Step 2 · Second approver (you)"}
          </p>
          {stage === "needs_proposal" ? (
            <SegmentedControl
              label="Outcome"
              value={choice}
              onChange={setChoice}
              segments={[
                { value: "release", label: "Release" },
                { value: "rework", label: "Rework" },
              ]}
            />
          ) : null}
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.note} className="type-small font-semibold text-ink">
              Your note (required)
            </label>
            <textarea
              id={ids.note}
              rows={3}
              maxLength={MAX_NOTE}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              aria-invalid={problem ? true : undefined}
              aria-describedby={problem ? ids.help : undefined}
              className={cn(
                "type-ops-body rounded-control border bg-white px-3 py-2.5 text-ink",
                problem ? "border-bad-fg" : "border-line-strong",
              )}
            />
            {problem ? (
              <p id={ids.help} role="alert" className="type-small text-bad-fg">
                {problem}
              </p>
            ) : null}
          </div>
          <Button className="self-start" loading={resolve.isPending} disabled={!online} onClick={submit}>
            {stage === "needs_proposal" ? `Propose ${outcome}` : `Approve ${outcome}`}
          </Button>
          <p className="type-small text-slate">
            {outcome === "release"
              ? stage === "needs_proposal"
                ? `Nothing moves yet. When a second ops person approves, the escrow partner is asked to pay ${formatMoney(amountMinor, "NGN")}.`
                : `Approving tells the escrow partner to pay ${formatMoney(amountMinor, "NGN")}. The client and contractor are told. It can't be undone.`
              : stage === "needs_proposal"
                ? `Nothing moves yet. When a second ops person approves, ${milestoneName} goes back to Funded.`
                : `Approving sends ${milestoneName} back to Funded. The money stays held while the contractor fixes it.`}
          </p>
        </div>
      )}

      {conflict ? (
        <Alert tone="warn" title={conflict.title}>
          {conflict.body}
        </Alert>
      ) : resolve.error ? (
        <Alert tone="bad" title="That didn't go through">
          Nothing changed and the money stays held. Try again.
        </Alert>
      ) : resolve.data && !resolve.data.resolved ? (
        <Alert tone="ok" title="Proposal recorded">
          A different ops person must now approve it.
        </Alert>
      ) : null}

      <p className="type-small flex items-start gap-2 rounded-card bg-mist p-3 text-slate">
        <Info aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
        Release and rework both need two different ops people choosing the same outcome.
      </p>
    </div>
  );
}

export function DisputeDetail({ disputeId, environment }: { disputeId: string; environment: string }) {
  const queue = useOpsQueue();
  const dispute = queue.data?.disputes.find((d) => d.dispute_id === disputeId);
  // Kept once seen: the second approval removes the dispute from the queue, and the outcome should stay on screen.
  const [last, setLast] = useState<QueueDispute | undefined>(undefined);
  if (dispute && dispute !== last) setLast(dispute);
  const shown = dispute ?? last;

  if (shown) return <DisputeBody dispute={shown} environment={environment} />;
  const header = <OpsHeader title={disputeRef(disputeId)} environment={environment} />;
  if (queue.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the dispute">
            <Skeleton className="h-64 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (!queue.data) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void queue.refetch()} />
      </>
    );
  }
  return (
    <>
      {header}
      <div className="flex flex-col items-start gap-3 p-5">
        <p className="text-slate">This dispute isn&apos;t open. Resolved disputes are in the audit log.</p>
        <Button asChild variant="outline">
          <Link href="/ops/disputes">Back to disputes</Link>
        </Button>
      </div>
    </>
  );
}

function DisputeBody({ dispute, environment }: { dispute: QueueDispute; environment: string }) {
  const project = useProject(dispute.project_id);
  const milestones = useMilestones(dispute.project_id);
  const m = milestones.data?.find((x) => x.id === dispute.milestone_id);
  const milestoneName = m?.name ?? "the milestone";
  const amount = m?.amount_minor ?? 0;

  if (project.isPending || milestones.isPending) {
    return (
      <>
        <OpsHeader title={disputeRef(dispute.dispute_id)} environment={environment} />
        <div className="p-5">
          <Loading label="Loading the dispute">
            <Skeleton className="h-64 w-full" />
          </Loading>
        </div>
      </>
    );
  }

  return (
    <>
      <OpsHeader
        title={`${disputeRef(dispute.dispute_id)} · ${project.data?.title ?? "Project"} · ${m?.name ?? "Milestone"}`}
        environment={environment}
      />
      <div className="grid grid-cols-3 items-start gap-4 p-5">
        <Timeline dispute={dispute} milestoneName={milestoneName} />
        <div className="flex flex-col gap-4">
          <Evidence dispute={dispute} />
          <Card className="flex flex-col gap-2 p-4">
            <CardLabel>Money held</CardLabel>
            <div className="type-ops-body flex justify-between gap-4">
              <span className="text-slate">{milestoneName} escrow</span>
              <span className="ibh-tabular font-semibold text-ink">{formatMoney(amount, "NGN")}</span>
            </div>
            <p className="type-small text-slate">{ESCROW_LINE}</p>
          </Card>
        </div>
        <Card className="flex flex-col gap-4 p-4">
          <h2 className="type-h3 text-ink">Resolution</h2>
          <Resolution dispute={dispute} milestoneName={milestoneName} amountMinor={amount} />
        </Card>
      </div>
    </>
  );
}
