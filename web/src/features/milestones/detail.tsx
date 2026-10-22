"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { milestoneActions } from "@/common/actions";
import { mockPayee } from "@/common/api/mocks";
import { useMock } from "@/common/api/mocks/context";
import { ApiError, toUiState } from "@/common/api/errors";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatDate } from "@/common/time";
import { formatFxRate, formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { MilestoneStepper } from "@/common/ui/milestone-stepper";
import { MoneyLarge } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip } from "@/common/ui/status-chip";

import { ActivityCard } from "./activity";
import { EvidenceChecklist, VerificationCard } from "./checklist";
import { MilestoneConflict } from "./conflict";
import { clientAmounts, MoneyCard } from "./money";
import { StatePanel } from "./state-panel";
import { useMilestone, type MilestoneView } from "./use-milestone";
import { useApprove } from "./writes";

// WEB-CLIENT-013 Milestone detail, all states, for the client. Approve and dispute show only on Verified and
// only to the project's client (common/actions.ts); the backend checks again on every request.

export function MilestoneDetailLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
      <Loading label="Loading the milestone">
        <Skeleton className="h-8 w-72" />
        <Skeleton className="h-24 w-full" />
        <Skeleton className="h-40 w-full" />
      </Loading>
    </div>
  );
}

function DetailRow({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate">{label}</dt>
      <dd className="ibh-tabular text-right font-semibold text-ink">{children}</dd>
    </div>
  );
}

/** The confirm step's wording (WEB-CLIENT-014 "3 · Confirm"), shared by the desktop dialog and the phone page. */
export function ConfirmDetails({ view, timeZone }: { view: MilestoneView; timeZone: string }) {
  const viewer = useViewer();
  const mockedPayee = useMock("MX-03");
  const { client, rate } = clientAmounts(view);
  const payee = mockedPayee ? mockPayee() : null;
  return (
    <dl className="type-small flex flex-col gap-2">
      <DetailRow label="Amount">
        {client ? `${formatMoney(client.amountMinor, client.currency)} · ` : ""}
        {formatMoney(view.milestone.amount_minor, "NGN")}
      </DetailRow>
      {client && rate ? (
        <DetailRow label={`Rate (at funding, ${formatDate(rate.on, timeZone)})`}>
          {formatFxRate(rate.fxRate, client.currency)}
        </DetailRow>
      ) : null}
      {payee ? (
        <>
          <DetailRow label="Paid to">{payee.name}</DetailRow>
          <DetailRow label="Bank account">
            {payee.bank} {payee.accountMasked}
          </DetailRow>
        </>
      ) : null}
      {viewer.fullName ? <DetailRow label="Approving as">{viewer.fullName}</DetailRow> : null}
    </dl>
  );
}

export function MilestoneDetail({ projectId, milestoneId }: { projectId: string; milestoneId: string }) {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const { view, error, loading, missing } = useMilestone(projectId, milestoneId);
  const approve = useApprove(projectId);
  const [confirming, setConfirming] = useState(false);

  if (loading) return <MilestoneDetailLoading />;
  if (missing) return <NotFoundContent />;
  if (error || !view) {
    const state = toUiState(error);
    return <ServerErrorContent reference={state.kind === "server" ? state.requestId : null} />;
  }

  const { milestone, milestones, project } = view;
  const base = `/projects/${projectId}/milestones/${milestoneId}`;
  if (approve.error instanceof ApiError && approve.error.status === 409) {
    return <MilestoneConflict name={milestone.name} status={milestone.status} href={base} />;
  }

  const actions = milestoneActions(milestone, project, viewer, { online });
  const { client, rate } = clientAmounts(view);
  const subline =
    milestone.status === "disputed"
      ? "Held. Release paused while iBackHome reviews"
      : client && rate
        ? `Funded ${formatDate(rate.on, timeZone)} at ${formatFxRate(rate.fxRate, client.currency)}`
        : null;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 pt-4 pb-28 sm:px-10 sm:py-6">
      {/* Phones: the screen's own compact header (WEB-CLIENT-013 mobile). */}
      <div className="flex items-center gap-3 sm:hidden">
        <Link
          href={`/projects/${projectId}/milestones`}
          aria-label="All milestones"
          className="flex size-11 items-center justify-center rounded-control"
        >
          <ChevronLeft aria-hidden strokeWidth={1.75} className="size-6 text-ink" />
        </Link>
        <h1 className="type-h3 flex-1 text-ink">{milestone.name}</h1>
        <StatusChip entity="milestone" state={milestone.status} audience="client" />
      </div>

      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <Link
            href={`/projects/${projectId}/milestones`}
            className="type-small font-semibold text-accent max-sm:hidden"
          >
            ‹ All milestones
          </Link>
          <p className="type-small text-slate">
            Milestone {milestone.sequence} of {milestones.length}
          </p>
          <div className="flex items-center gap-3 max-sm:hidden">
            <h1 className="type-h1 text-ink">{milestone.name}</h1>
            <StatusChip entity="milestone" state={milestone.status} audience="client" />
          </div>
        </div>
        <div className="flex flex-col gap-0.5 sm:items-end">
          <MoneyLarge ngnMinor={milestone.amount_minor} client={client} className="max-sm:items-start" />
          {subline ? <p className="type-small text-muted">{subline}</p> : null}
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          <MilestoneStepper milestone={milestone} timeZone={timeZone} />
          <StatePanel
            view={view}
            actions={actions}
            timeZone={timeZone}
            base={base}
            onApprove={() => setConfirming(true)}
          />
          <EvidenceChecklist view={view} timeZone={timeZone} projectBase={`/projects/${projectId}`} />
          <VerificationCard view={view} timeZone={timeZone} />
        </div>
        <aside className="flex flex-col gap-6">
          <MoneyCard view={view} timeZone={timeZone} />
          <ActivityCard view={view} timeZone={timeZone} />
        </aside>
      </div>

      {/* Phones: the decision stays in reach (WEB-CLIENT-013 mobile, verified). */}
      {actions.has("approve") || actions.has("raise_dispute") || actions.has("fund") ? (
        <div className="fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 border-t border-line bg-white p-4 sm:hidden">
          {actions.has("fund") ? (
            <Button asChild size="lg" block>
              <Link href={`/projects/${milestone.project_id}/fund/${milestone.id}`}>Fund this milestone</Link>
            </Button>
          ) : null}
          {actions.has("approve") ? (
            <Button asChild size="lg" block>
              <Link href={`${base}/approve`}>Approve release</Link>
            </Button>
          ) : null}
          {actions.has("raise_dispute") ? (
            <Button asChild size="lg" block variant="outline">
              <Link href={`${base}/dispute`}>Raise a dispute</Link>
            </Button>
          ) : null}
        </div>
      ) : null}

      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => !approve.isPending && setConfirming(open)}
        aboutMoney
        busy={approve.isPending}
        title={`Release ${client ? formatMoney(client.amountMinor, client.currency) : formatMoney(milestone.amount_minor, "NGN")} to the contractor?`}
        description={
          <span className="flex flex-col gap-3">
            <ConfirmDetails view={view} timeZone={timeZone} />
            <span>Once confirmed, the release can&apos;t be undone or disputed.</span>
          </span>
        }
        confirmLabel="Confirm and release"
        onConfirm={() =>
          approve.mutate(milestone.id, {
            onSuccess: () => setConfirming(false),
            onError: () => setConfirming(false),
          })
        }
      />
      {approve.error && !(approve.error instanceof ApiError && approve.error.status === 409) ? (
        <p role="alert" className="text-bad-fg">
          We couldn&apos;t send your approval. Nothing was released. Try again.
        </p>
      ) : null}
    </div>
  );
}
