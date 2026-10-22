"use client";

import { ChevronLeft, CircleCheck } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { milestoneActions } from "@/common/actions";
import { ApiError } from "@/common/api/errors";
import { useViewer } from "@/common/auth/viewer";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatDate } from "@/common/time";
import { formatFxRate, formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { EscrowTrustLine } from "@/common/ui/money-display";
import { Card } from "@/common/ui/surfaces";
import { Time } from "@/common/ui/time";

import { MilestoneConflict } from "./conflict";
import { ConfirmDetails, MilestoneDetailLoading } from "./detail";
import { clientAmounts } from "./money";
import { useMilestone } from "./use-milestone";
import { useApprove } from "./writes";

// WEB-CLIENT-014 Approve a release, the phone flow: tap 1 is "Approve release" on the milestone, tap 2 the review
// here, tap 3 "Confirm and release". Only a verified milestone of the viewer's own project can be approved; any
// other state shows what happened instead (the backend refuses it anyway, 409).

export function ApproveFlow({ projectId, milestoneId }: { projectId: string; milestoneId: string }) {
  const router = useRouter();
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const { view, error, loading, missing } = useMilestone(projectId, milestoneId);
  const approve = useApprove(projectId);
  const [step, setStep] = useState<"review" | "confirm">("review");

  if (loading) return <MilestoneDetailLoading />;
  if (missing) return <NotFoundContent />;
  if (error || !view) return <ServerErrorContent reference={null} />;

  const { milestone, project } = view;
  const base = `/projects/${projectId}/milestones/${milestoneId}`;
  const conflict = approve.error instanceof ApiError && approve.error.status === 409;
  if (conflict || !milestoneActions(milestone, project, viewer, { online: true }).has("approve")) {
    return <MilestoneConflict name={milestone.name} status={milestone.status} href={base} />;
  }

  const { client, rate } = clientAmounts(view);
  const amount = client
    ? formatMoney(client.amountMinor, client.currency)
    : formatMoney(milestone.amount_minor, "NGN");
  const verification = milestone.latest_verification;
  const items = verification?.checklist.length ?? 0;

  return (
    <div className="mx-auto flex w-full max-w-xl flex-col gap-5 px-4 pt-4 pb-40 sm:py-8">
      <div className="flex items-center gap-3">
        <Link
          href={step === "confirm" ? "#" : base}
          onClick={(e) => {
            if (step === "confirm") {
              e.preventDefault();
              setStep("review");
            }
          }}
          aria-label="Back"
          className="flex size-11 items-center justify-center rounded-control"
        >
          <ChevronLeft aria-hidden strokeWidth={1.75} className="size-6 text-ink" />
        </Link>
        <h1 className="type-h3 text-ink">
          {step === "review" ? `Approve ${milestone.name}` : `Release ${amount} to the contractor?`}
        </h1>
      </div>

      {step === "review" ? (
        <>
          <Card className="flex flex-col gap-1 p-5">
            <p className="type-small text-slate">Release to the contractor</p>
            <p className="ibh-tabular type-h2 text-ink">{amount}</p>
            {client ? (
              <p className="ibh-tabular text-slate">{formatMoney(milestone.amount_minor, "NGN")}</p>
            ) : null}
            {client && rate ? (
              <p className="type-small text-muted">
                {formatFxRate(rate.fxRate, client.currency)}, the rate when you funded on{" "}
                {formatDate(rate.on, timeZone)}
              </p>
            ) : null}
          </Card>
          <Card className="flex flex-col gap-4 p-5">
            <div className="flex gap-3">
              <CircleCheck aria-hidden strokeWidth={1.75} className="mt-0.5 size-5 flex-none text-ok-fg" />
              <div>
                <p className="font-semibold text-ink">Checklist complete</p>
                <p className="type-small text-slate">
                  {items} of {items} {items === 1 ? "item" : "items"} captured and accepted
                </p>
              </div>
            </div>
            {verification ? (
              <div className="flex gap-3">
                <CircleCheck aria-hidden strokeWidth={1.75} className="mt-0.5 size-5 flex-none text-ok-fg" />
                <div>
                  <p className="font-semibold text-ink">Verified by the supervisor</p>
                  <p className="type-small text-slate">
                    <Time iso={verification.created_at} timeZone={timeZone} />, on site
                  </p>
                </div>
              </div>
            ) : null}
            <div className="flex gap-3">
              <CircleCheck aria-hidden strokeWidth={1.75} className="mt-0.5 size-5 flex-none text-ok-fg" />
              <div>
                <p className="font-semibold text-ink">All three checks passed</p>
                <p className="type-small text-slate">
                  Inside the boundary · signature valid · not reused or edited
                </p>
              </div>
            </div>
            <Link href={base} className="type-small font-semibold text-accent underline">
              See the full checklist and notes ›
            </Link>
          </Card>
          <div className="fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 border-t border-line bg-white p-4 sm:static sm:border-0 sm:bg-transparent sm:p-0">
            <Button size="lg" block disabled={!online} onClick={() => setStep("confirm")}>
              Approve release
            </Button>
            <Button asChild size="lg" block variant="outline">
              <Link href={`${base}/dispute`}>Raise a dispute</Link>
            </Button>
          </div>
        </>
      ) : (
        <>
          <Card className="flex flex-col gap-4 p-5">
            <ConfirmDetails view={view} timeZone={timeZone} />
            <p className="type-small text-slate">
              Once confirmed, the release can&apos;t be undone or disputed.
            </p>
          </Card>
          {approve.error ? (
            <p role="alert" className="text-bad-fg">
              We couldn&apos;t send your approval. Nothing was released. Try again.
            </p>
          ) : null}
          <div className="fixed inset-x-0 bottom-0 z-30 flex flex-col gap-2 border-t border-line bg-white p-4 sm:static sm:border-0 sm:bg-transparent sm:p-0">
            <Button
              size="lg"
              block
              disabled={!online}
              loading={approve.isPending}
              onClick={() => approve.mutate(milestone.id, { onSuccess: () => router.replace(base) })}
            >
              Confirm and release
            </Button>
            <Button
              size="lg"
              block
              variant="secondary"
              disabled={approve.isPending}
              onClick={() => setStep("review")}
            >
              Cancel
            </Button>
            <EscrowTrustLine className="justify-center" />
          </div>
        </>
      )}
    </div>
  );
}
