"use client";

import { ChevronDown, CircleCheck, Sparkles } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useProject } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ConfirmDialog } from "@/common/ui/dialog";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { needsSubscription } from "../subscriptions/state";
import { useApproveBoq, useBoq, type Boq } from "./api";

// WEB-CLIENT-005 BoQ review and approval at /projects/:id/boq. Amounts are naira (the BoQ's currency); the
// "≈ £" estimates need a rate the backend only gives when funding (W6b), so they aren't shown. "Send back for
// changes" needs MX-08 and isn't built. The client's approval is the last of three (any order); the final one
// needs a saved site (409 site_not_set) and makes the project active, creating the milestones.

const ROLES: { role: string; name: string }[] = [
  { role: "contractor", name: "Your contractor" },
  { role: "ops", name: "iBackHome ops" },
  { role: "client", name: "You" },
];

function share(part: number, total: number): string {
  return total > 0 ? `${Math.round((part / total) * 100)}%` : "–";
}

function MilestoneLines({
  m,
  open,
  onToggle,
}: {
  m: Boq["milestones"][number];
  open: boolean;
  onToggle: () => void;
}) {
  const id = `boq-${m.sequence}`;
  return (
    <Card className="overflow-hidden">
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={id}
          onClick={onToggle}
          className="flex w-full items-center justify-between gap-4 px-5 py-4 text-left"
        >
          <span className="font-semibold text-ink">
            {m.sequence} · {m.name} · {m.items.length} {m.items.length === 1 ? "line" : "lines"}
          </span>
          <span className="flex items-center gap-3">
            <span className="ibh-tabular font-semibold text-ink">{formatMoney(m.amount_minor, "NGN")}</span>
            <ChevronDown
              aria-hidden
              strokeWidth={1.75}
              className={cn("size-5 text-slate", open && "rotate-180")}
            />
          </span>
        </button>
      </h3>
      {open ? (
        <div id={id} className="border-t border-line">
          <Table caption={`${m.name} lines`} className="rounded-none border-0">
            <thead>
              <tr>
                <Th>Line</Th>
                <Th>Description</Th>
                <Th>Unit</Th>
                <Th numeric>Qty</Th>
                <Th numeric>Unit price</Th>
                <Th numeric>Total</Th>
              </tr>
            </thead>
            <tbody>
              {m.items.map((line) => (
                <Tr key={line.id}>
                  <Td className="type-mono">
                    {m.sequence}.{line.line_no}
                  </Td>
                  <Td>{line.description}</Td>
                  <Td>{line.unit}</Td>
                  <Td numeric>{line.quantity}</Td>
                  <Td numeric>{formatMoney(line.unit_price_minor, "NGN")}</Td>
                  <Td numeric>{formatMoney(line.total_minor, "NGN")}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
          <p className="type-small border-t border-line px-5 py-3 text-slate">
            Totals are calculated by iBackHome: quantity × unit price, rounded to the nearest kobo.
          </p>
        </div>
      ) : null}
    </Card>
  );
}

export function BoqReview({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const project = useProject(projectId);
  const boq = useBoq(projectId);
  const approve = useApproveBoq(projectId);
  const [open, setOpen] = useState<Set<number>>(new Set([1]));
  const [confirming, setConfirming] = useState(false);

  if (project.isPending || boq.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the BoQ">
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  if (!project.data || !boq.data)
    return <ServerErrorContent reference={null} onRetry={() => void boq.refetch()} />;

  const p = project.data;
  const b = boq.data;
  const total = b.boq_total_minor;
  const over = total - b.budget_minor;
  const lines = b.milestones.reduce((n, m) => n + m.items.length, 0);
  const waitingForMe = b.project_status === "boq_review" && b.approvals_missing.includes("client");
  const approvedNow = approve.isSuccess || ["active", "paused", "completed"].includes(b.project_status);
  const approvalAt = (role: string) => b.approvals.find((a) => a.role === role)?.approved_at;
  const lastOne = b.approvals_missing.length === 1 && waitingForMe;
  const siteMissing = !p.site;
  const conflict = approve.error instanceof ApiError ? approve.error.code : null;

  if (!b.milestones.length) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <h2 className="sr-only">BoQ</h2>
        <Card className="p-6 text-slate">
          Your contractor hasn&apos;t submitted the bill of quantities yet.
        </Card>
      </div>
    );
  }

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        <h2 className="sr-only">BoQ</h2>
        {approvedNow && b.project_status !== "boq_review" ? (
          <Alert tone="ok" title="Your project is active">
            You, your contractor and our team approved the BoQ. The milestones have been created and the site
            is now locked.
          </Alert>
        ) : null}
        {over > 0 ? (
          <Alert tone="warn" title="This BoQ is above your budget">
            <span className="ibh-tabular block">
              BoQ total {formatMoney(total, "NGN")} · your budget {formatMoney(b.budget_minor, b.currency)} ·{" "}
              {formatMoney(over, "NGN")} over
            </span>
            {waitingForMe
              ? "You can still approve it, or ask your contractor to revise it before you do."
              : null}
          </Alert>
        ) : null}
        <Table caption="Milestones">
          <thead>
            <tr>
              <Th>#</Th>
              <Th>Milestone</Th>
              <Th numeric>Lines</Th>
              <Th numeric>Amount</Th>
              <Th numeric>Share</Th>
            </tr>
          </thead>
          <tbody>
            {b.milestones.map((m) => (
              <Tr key={m.sequence}>
                <Td>{m.sequence}</Td>
                <Td className="font-semibold">{m.name}</Td>
                <Td numeric>{m.items.length}</Td>
                <Td numeric>{formatMoney(m.amount_minor, "NGN")}</Td>
                <Td numeric>{share(m.amount_minor, total)}</Td>
              </Tr>
            ))}
            <Tr className="font-semibold">
              <Td />
              <Td>Total</Td>
              <Td numeric>{lines}</Td>
              <Td numeric>{formatMoney(total, "NGN")}</Td>
              <Td numeric>100%</Td>
            </Tr>
          </tbody>
        </Table>
        {b.milestones.map((m) => (
          <MilestoneLines
            key={m.sequence}
            m={m}
            open={open.has(m.sequence)}
            onToggle={() =>
              setOpen((s) => {
                const next = new Set(s);
                if (next.has(m.sequence)) next.delete(m.sequence);
                else next.add(m.sequence);
                return next;
              })
            }
          />
        ))}
      </div>

      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-4 p-5">
          <CardLabel>
            Approvals {b.approvals.length} of {ROLES.length}
          </CardLabel>
          <ul className="flex flex-col gap-3">
            {ROLES.map(({ role, name }) => {
              const at = approvalAt(role);
              return (
                <li key={role} className="flex items-center justify-between gap-3">
                  <span className="flex flex-col">
                    <span className="font-semibold text-ink">{name}</span>
                    <span className="type-small text-slate">
                      {at
                        ? formatDateTime(at, timeZone)
                        : role === "client"
                          ? "Waiting for your review"
                          : "Waiting"}
                    </span>
                  </span>
                  <ToneChip label={at ? "Approved" : "Waiting"} tone={at ? "ok" : "neutral"} size="small" />
                </li>
              );
            })}
          </ul>
          {waitingForMe && !approve.isSuccess ? (
            <>
              <p className="type-small flex items-center gap-2 text-slate">
                <CircleCheck
                  aria-hidden
                  strokeWidth={1.75}
                  className={cn("size-4", siteMissing ? "text-muted" : "text-ok-fg")}
                />
                {siteMissing
                  ? "Save your site first — it's needed before the final approval"
                  : "Site saved — required before the final approval"}
              </p>
              {lastOne ? (
                <p className="type-small text-slate">
                  Your approval is the last one. When you approve, the {b.milestones.length} milestones are
                  created and the project becomes active.
                </p>
              ) : null}
              {conflict === "site_not_set" ? (
                <Alert tone="warn" title="Save your site first">
                  <Link href={`/projects/${p.id}/site`} className="underline">
                    Pin the site and draw its boundary
                  </Link>
                  , then approve.
                </Alert>
              ) : needsSubscription(conflict) ? (
                <Alert tone="warn" title="Start the monthly supervision first">
                  <Link href={`/projects/${p.id}/subscription`} className="underline">
                    Set up the supervision subscription
                  </Link>
                  , then approve.
                </Alert>
              ) : approve.error ? (
                <Alert tone="warn" title="The BoQ changed or was already approved">
                  Nothing was approved twice. The page shows where it is now.
                </Alert>
              ) : null}
              <Button size="lg" block onClick={() => setConfirming(true)} disabled={lastOne && siteMissing}>
                Approve BoQ
              </Button>
            </>
          ) : b.project_status === "boq_review" ? (
            <p className="type-small text-slate">You&apos;ve approved. Waiting for the others.</p>
          ) : null}
        </Card>
        <Card className="flex flex-col gap-2 p-5">
          <CardLabel className="flex items-center gap-2">
            <Sparkles aria-hidden strokeWidth={1.75} className="size-4" />
            AI quote check
          </CardLabel>
          <p className="type-small text-slate">
            Compare these prices with what our partner suppliers charge this month. Advisory only.
          </p>
          <Link
            href={`/projects/${p.id}/boq/check`}
            className="type-small rounded-control font-semibold text-accent"
          >
            Check this BoQ ›
          </Link>
        </Card>
        <p className="type-small text-slate">{ESCROW_LINE}</p>
      </aside>

      <ConfirmDialog
        open={confirming}
        onOpenChange={(o) => !approve.isPending && setConfirming(o)}
        busy={approve.isPending}
        title="Approve this BoQ?"
        description={
          lastOne
            ? `Yours is the last approval: the ${b.milestones.length} milestones are created, the project becomes active and the site is locked. No money moves until you fund a milestone.`
            : "Your approval is recorded. The milestones are created once your contractor and our team have approved too. No money moves until you fund a milestone."
        }
        confirmLabel="Approve BoQ"
        onConfirm={() => approve.mutate(null, { onSettled: () => setConfirming(false) })}
      />
    </div>
  );
}
