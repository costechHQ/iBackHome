"use client";

import { useQueries } from "@tanstack/react-query";
import { FileText, House, MapPin, Plus, Scale, Wallet } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { keys, ledgerQuery, useProjects, type Milestone } from "@/common/api/queries";
import { useViewer } from "@/common/auth/viewer";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDate, formatDateTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { projectKeys } from "@/features/projects/api";
import { ProjectRow } from "@/features/projects/project-row";
import { nextAction } from "@/features/projects/setup";
import { reportsQuery } from "@/features/reports/reports";

import { moneySummary } from "./money-summary";

// WEB-CLIENT-008 Client home at /projects (the public site keeps "/", decided 2026-10-22): what needs the
// client across their projects, then the projects. Attention items: milestones verified and waiting for
// approval, a weekly report sent in the last 8 days, and set-up steps that are the client's to do. The
// notification feed (MX-11) and contractor invitations (MX-02) aren't available, so they aren't listed.

type Item = {
  key: string;
  icon: typeof Scale;
  title: string;
  detail: string;
  amount?: { client: string | null; ngn: string };
  href: string;
  action: string;
  primary?: boolean;
};

const RECENT_REPORT_MS = 8 * 24 * 60 * 60 * 1000;

function greeting(timeZone: string, name: string | null) {
  const hour = Number(
    new Intl.DateTimeFormat("en-GB", { timeZone, hour: "2-digit", hourCycle: "h23" }).format(new Date()),
  );
  const part = hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";
  return name ? `${part}, ${name.split(/\s+/)[0]}` : part;
}

export function ClientHome() {
  const viewer = useViewer();
  const timeZone = useViewerTimeZone();
  const projects = useProjects();
  // When the page opened, for "sent in the last 8 days" (render stays pure).
  const [openedAt] = useState(() => Date.now());
  const list = projects.data?.items ?? [];
  const details = useQueries({
    queries: list.flatMap((p) => [
      {
        queryKey: keys.milestones(p.id),
        queryFn: () =>
          call(
            api().GET("/api/v1/projects/{project_id}/milestones", { params: { path: { project_id: p.id } } }),
          ),
      },
      {
        queryKey: keys.project(p.id),
        queryFn: () =>
          call(api().GET("/api/v1/projects/{project_id}", { params: { path: { project_id: p.id } } })),
      },
      {
        queryKey: projectKeys.boq(p.id),
        retry: false,
        queryFn: () =>
          call(api().GET("/api/v1/projects/{project_id}/boq", { params: { path: { project_id: p.id } } })),
      },
      ledgerQuery(p.id),
      reportsQuery(p.id),
    ]),
  });

  if (projects.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-12">
        <Loading label="Loading your projects">
          <Skeleton className="h-9 w-72" />
          <Skeleton className="h-40 w-full" />
        </Loading>
      </div>
    );
  if (!projects.data) return <ServerErrorContent reference={null} onRetry={() => void projects.refetch()} />;

  const items: Item[] = [];
  list.forEach((p, i) => {
    const [milestones, detail, boq, ledger, reports] = details.slice(i * 5, i * 5 + 5);
    const ms = (milestones?.data ?? []) as Milestone[];
    const project = detail?.data as
      { status: string; site?: unknown; contractor_id?: string | null } | undefined;
    const ledgerData = ledger?.data as { ledger: Parameters<typeof moneySummary>[1] } | undefined;
    const summary = ledgerData ? moneySummary(ms, ledgerData.ledger) : null;
    for (const m of ms.filter((x) => x.status === "verified")) {
      const pay = summary?.money.get(m.id)?.payment;
      items.push({
        key: `approve-${m.id}`,
        icon: Scale,
        title: `${m.name} is verified — approve to release`,
        detail: `${p.title}${m.latest_verification ? ` · verified ${formatDate(m.latest_verification.created_at, timeZone)}` : ""}`,
        amount: {
          client: pay ? formatMoney(pay.netMinor, pay.currency) : null,
          ngn: formatMoney(m.amount_minor, "NGN"),
        },
        href: `/projects/${p.id}/milestones/${m.id}`,
        action: "Review and approve",
        primary: true,
      });
    }
    const latest = (
      reports?.data as { id: string; week_start: string; sent_at: string | null }[] | undefined
    )?.[0];
    if (latest?.sent_at && openedAt - new Date(latest.sent_at).getTime() < RECENT_REPORT_MS) {
      items.push({
        key: `report-${latest.id}`,
        icon: FileText,
        title: "Weekly report is ready",
        detail: `${p.title} · week of ${formatDate(latest.week_start, timeZone)} · reviewed by your supervisor`,
        href: `/projects/${p.id}/reports/${latest.id}`,
        action: "Read report",
      });
    }
    if (project) {
      const next = nextAction(project, boq?.data as { approvals_missing: string[] } | undefined, ms);
      if (next && next.kind !== "wait") {
        const pending = [...ms].sort((a, b) => a.sequence - b.sequence).find((x) => x.status === "pending");
        items.push({
          key: `setup-${p.id}`,
          icon: next.kind === "site" ? MapPin : next.kind === "fund" ? Wallet : Scale,
          title: next.label,
          detail: p.title,
          href:
            next.kind === "site"
              ? `/projects/${p.id}/site`
              : next.kind === "review_boq"
                ? `/projects/${p.id}/boq`
                : pending
                  ? `/projects/${p.id}/fund/${pending.id}`
                  : `/projects/${p.id}`,
          action:
            next.kind === "site"
              ? "Pin your site"
              : next.kind === "review_boq"
                ? "Review the BoQ"
                : "Fund it",
        });
      }
    }
  });

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-8 px-4 py-8 sm:px-12">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="flex flex-col gap-1">
          <p className="type-small text-slate">{formatDateTime(new Date().toISOString(), timeZone)}</p>
          <h1 className="type-h1 text-ink">{greeting(timeZone, viewer.fullName)}</h1>
        </div>
        {list.length ? (
          <Button asChild size="lg">
            <Link href="/projects/new">
              <Plus aria-hidden strokeWidth={2} className="size-5" />
              New project
            </Link>
          </Button>
        ) : null}
      </div>

      {items.length ? (
        <section className="flex flex-col gap-3">
          <h2 className="type-h3 text-ink">Needs your attention · {items.length}</h2>
          <Card className="overflow-hidden">
            <ul>
              {items.map((it) => (
                <li
                  key={it.key}
                  className="flex flex-wrap items-center gap-4 border-b border-line px-5 py-4 last:border-b-0"
                >
                  <span className="flex size-10 flex-none items-center justify-center rounded-control bg-mist text-navy-900">
                    <it.icon aria-hidden strokeWidth={1.75} className="size-5" />
                  </span>
                  <div className="flex min-w-0 flex-1 flex-col gap-0.5">
                    <p className="font-semibold text-ink">{it.title}</p>
                    <p className="type-small text-slate">{it.detail}</p>
                  </div>
                  {it.amount ? (
                    <span className="ibh-tabular flex flex-col items-end">
                      <span className="font-semibold text-ink">{it.amount.client ?? it.amount.ngn}</span>
                      {it.amount.client ? (
                        <span className="type-small text-slate">{it.amount.ngn}</span>
                      ) : null}
                    </span>
                  ) : null}
                  <Button asChild variant={it.primary ? "primary" : "outline"}>
                    <Link href={it.href}>{it.action}</Link>
                  </Button>
                </li>
              ))}
            </ul>
          </Card>
          <p className="type-small text-slate">{ESCROW_LINE}</p>
        </section>
      ) : null}

      <section className="flex flex-col gap-3">
        <h2 className="type-h3 text-ink">Your projects</h2>
        {list.length ? (
          <ul className="flex flex-col gap-4">
            {list.map((p) => (
              <li key={p.id}>
                <ProjectRow id={p.id} />
              </li>
            ))}
          </ul>
        ) : (
          <Card>
            <EmptyState
              icon={House}
              title="No projects yet"
              action={
                <Button asChild size="lg">
                  <Link href="/projects/new">Create your first project</Link>
                </Button>
              }
            >
              Start with your site address, a budget, and your contractor&apos;s phone number.
            </EmptyState>
          </Card>
        )}
      </section>
    </div>
  );
}
