"use client";

import { Sparkles } from "lucide-react";
import Link from "next/link";

import {
  shortId,
  useEvidence,
  useLedger,
  useMilestones,
  useProject,
  type Milestone,
} from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatFxRate, formatMoney } from "@/common/money";
import { formatDate, formatDateTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { EvidenceCard } from "@/common/ui/evidence";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { summaryOf } from "@/common/ui/markdown";
import { useReports } from "@/features/reports/reports";

import { moneySummary, type ClientAmount } from "./money-summary";

// WEB-CLIENT-009 Project overview at /projects/:id (active projects; a project being set up opens its set-up
// tracker). What needs the client, progress, spend against budget, milestones, the latest evidence and weekly
// report, and the money in escrow now. Money in the client's currency where the ledger allows, else naira.
// Not shown yet: the supervisor card, visit history and spot checks (MX-24, MX-14), the contractor card
// (MX-26), and the live walkthrough (P2, a placeholder elsewhere).

function Amount({ client, ngn }: { client: ClientAmount | null; ngn: bigint | number }) {
  return (
    <span className="ibh-tabular flex flex-col items-end">
      <span className="font-semibold text-ink">
        {client ? formatMoney(client.amountMinor, client.currency) : formatMoney(ngn, "NGN")}
      </span>
      {client ? <span className="type-small text-slate">{formatMoney(ngn, "NGN")}</span> : null}
    </span>
  );
}

export function ProjectOverview({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);
  const ledger = useLedger(projectId);
  const evidence = useEvidence(projectId);
  const reports = useReports(projectId);

  if (project.isPending || milestones.isPending || ledger.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the project">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  if (!project.data || !milestones.data || !ledger.data)
    return <ServerErrorContent reference={null} onRetry={() => void milestones.refetch()} />;

  const p = project.data;
  const ms = [...(milestones.data as Milestone[])].sort((a, b) => a.sequence - b.sequence);
  const s = moneySummary(ms, ledger.data.ledger);
  const released = ms.filter((m) => m.status === "released").length;
  const current = ms.find((m) => m.status !== "released");
  const nextToFund = ms.find((m) => m.status === "pending");
  const verified = ms.filter((m) => m.status === "verified");
  const over = s.boqNgn - BigInt(p.budget_minor);
  const latest = (evidence.data ?? []).filter((e) => e.status !== "rejected").slice(0, 4);
  const acceptedCount = (evidence.data ?? []).filter((e) => e.status === "accepted").length;
  const report = reports.data?.[0];
  const held = ms.filter((m) => m.funded_at && m.status !== "released");

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-10 lg:grid-cols-3">
      <h2 className="sr-only">Overview</h2>
      <div className="flex flex-col gap-6 lg:col-span-2">
        {verified.map((m) => {
          const pay = s.money.get(m.id)?.payment;
          return (
            <Card key={m.id} className="flex flex-col gap-4 border-2 border-navy-900 p-6">
              <CardLabel>Needs your approval</CardLabel>
              <div className="flex flex-wrap items-start justify-between gap-4">
                <h3 className="type-h2 text-ink">{m.name} is verified — approve to release</h3>
                <Amount
                  client={pay ? { amountMinor: pay.netMinor, currency: pay.currency } : null}
                  ngn={m.amount_minor}
                />
              </div>
              {m.latest_verification ? (
                <p className="text-slate">
                  The supervisor verified it on {formatDateTime(m.latest_verification.created_at, timeZone)}.
                </p>
              ) : null}
              <div className="flex flex-wrap gap-3">
                <Button asChild size="lg">
                  <Link href={`/projects/${p.id}/milestones/${m.id}`}>Review and approve</Link>
                </Button>
                <Button asChild size="lg" variant="outline">
                  <Link href={`/projects/${p.id}/evidence?milestone=${m.id}`}>See the evidence</Link>
                </Button>
              </div>
              <p className="type-small text-slate">{ESCROW_LINE}</p>
            </Card>
          );
        })}

        <div className="grid gap-4 sm:grid-cols-2">
          <Card className="flex flex-col gap-3 p-5">
            <CardLabel>Progress</CardLabel>
            <p className="type-h3 text-ink">
              {released} of {ms.length} milestones released
            </p>
            <div
              role="progressbar"
              aria-label={`${released} of ${ms.length} milestones released`}
              aria-valuemin={0}
              aria-valuemax={ms.length}
              aria-valuenow={released}
              className="h-2 overflow-hidden rounded-pill bg-line"
            >
              <div
                className="h-full bg-navy-900"
                style={{ width: `${ms.length ? Math.round((released / ms.length) * 100) : 0}%` }}
              />
            </div>
            <p className="type-small text-slate">
              {current ? `${current.name}: ${current.status}. ` : ""}
              {nextToFund ? `Next to fund: ${nextToFund.name}.` : "Every milestone is funded."}
            </p>
          </Card>
          <Card className="flex flex-col gap-3 p-5">
            <CardLabel>Spend vs budget</CardLabel>
            <p className="ibh-tabular type-h3 text-ink">{formatMoney(s.boqNgn, "NGN")} BoQ</p>
            <p className="type-small text-slate">
              Budget {formatMoney(p.budget_minor, p.currency)}
              {over > 0n ? ` · ${formatMoney(over, "NGN")} over` : ""}
            </p>
            <dl className="type-small grid grid-cols-3 gap-2">
              <div>
                <dt className="text-slate">Released</dt>
                <dd className="ibh-tabular font-semibold text-ink">
                  {s.releasedClient
                    ? formatMoney(s.releasedClient.amountMinor, s.releasedClient.currency)
                    : formatMoney(s.releasedNgn, "NGN")}
                </dd>
              </div>
              <div>
                <dt className="text-slate">In escrow</dt>
                <dd className="ibh-tabular font-semibold text-ink">
                  {s.escrow.client
                    ? formatMoney(s.escrow.client.amountMinor, s.escrow.client.currency)
                    : formatMoney(s.escrow.ngnMinor, "NGN")}
                </dd>
              </div>
              <div>
                <dt className="text-slate">Not funded</dt>
                <dd className="ibh-tabular font-semibold text-ink">{formatMoney(s.notFundedNgn, "NGN")}</dd>
              </div>
            </dl>
          </Card>
        </div>

        <Card className="overflow-hidden">
          <div className="flex items-center justify-between border-b border-line px-5 py-3">
            <h3 className="type-h3 text-ink">Milestones</h3>
            <Link
              href={`/projects/${p.id}/milestones`}
              className="type-small rounded-control font-semibold text-accent"
            >
              All milestones ›
            </Link>
          </div>
          <ul>
            {ms.map((m) => {
              const pay = s.money.get(m.id)?.payment;
              return (
                <li key={m.id} className="border-b border-line last:border-b-0">
                  <Link
                    href={`/projects/${p.id}/milestones/${m.id}`}
                    className="flex items-center gap-4 px-5 py-3 hover:bg-row-highlight"
                  >
                    <span className="type-small w-6 text-slate">{m.sequence}</span>
                    <span className="flex-1 font-semibold text-ink">{m.name}</span>
                    <StatusChip entity="milestone" state={m.status} audience="client" size="small" />
                    <span className="w-36 text-right">
                      <Amount
                        client={pay ? { amountMinor: pay.netMinor, currency: pay.currency } : null}
                        ngn={m.amount_minor}
                      />
                    </span>
                  </Link>
                </li>
              );
            })}
          </ul>
        </Card>

        <section className="flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="type-h3 text-ink">Latest evidence · {acceptedCount} accepted in total</h3>
            <Link
              href={`/projects/${p.id}/evidence`}
              className="type-small rounded-control font-semibold text-accent"
            >
              Evidence gallery ›
            </Link>
          </div>
          {latest.length ? (
            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              {latest.map((e) => (
                <li key={e.id}>
                  <EvidenceCard
                    item={e}
                    audience="client"
                    reference={`EV-${shortId(e.id)}`}
                    time={formatDate(e.captured_at, timeZone)}
                  />
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-slate">
              No evidence yet. The supervisor captures it on site once work starts.
            </p>
          )}
        </section>

        {report ? (
          <Card className="flex flex-col gap-3 p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <h3 className="type-h3 text-ink">
                Latest weekly report · week of {formatDate(report.week_start, timeZone)}
              </h3>
              <span className="flex gap-2">
                <ToneChip label="AI-generated" tone="info" size="small" />
                <ToneChip label="Reviewed by supervisor" tone="ok" size="small" />
              </span>
            </div>
            <p className="flex items-start gap-2 text-slate">
              <Sparkles aria-hidden strokeWidth={1.75} className="mt-1 size-4 flex-none" />
              {summaryOf(report.body_md)}
            </p>
            <Link
              href={`/projects/${p.id}/reports/${report.id}`}
              className="type-small self-start rounded-control font-semibold text-accent"
            >
              Read the full report ›
            </Link>
          </Card>
        ) : null}
      </div>

      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>In escrow now</CardLabel>
          <p className="ibh-tabular type-h2 text-ink">
            {s.escrow.client
              ? formatMoney(s.escrow.client.amountMinor, s.escrow.client.currency)
              : formatMoney(s.escrow.ngnMinor, "NGN")}
          </p>
          {s.escrow.client ? (
            <p className="ibh-tabular text-slate">{formatMoney(s.escrow.ngnMinor, "NGN")}</p>
          ) : null}
          {held.length ? (
            <ul className="type-small flex flex-col gap-1 text-slate">
              {held.map((m) => {
                const pay = s.money.get(m.id)?.payment;
                return (
                  <li key={m.id}>
                    For {m.name}
                    {m.funded_at ? `, funded ${formatDate(m.funded_at, timeZone)}` : ""}
                    {pay?.fxRate ? ` at ${formatFxRate(pay.fxRate, pay.currency)}` : ""}.
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="type-small text-slate">Nothing is held right now.</p>
          )}
          <p className="type-small text-slate">{ESCROW_LINE}</p>
          <Link
            href={`/projects/${p.id}/ledger`}
            className="type-small self-start rounded-control font-semibold text-accent"
          >
            Open the ledger ›
          </Link>
        </Card>
      </aside>
    </div>
  );
}
