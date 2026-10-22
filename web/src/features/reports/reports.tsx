"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Sparkles } from "lucide-react";
import Link from "next/link";

import { api, call } from "@/common/api/client";
import type { components } from "@/common/api/schema";
import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatDate, formatDateTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";

import { Markdown, summaryOf } from "@/common/ui/markdown";

// WEB-CLIENT-018 Weekly reports: the list and one report. The client sees a report only once the supervisor
// (or ops) has reviewed it: the backend also lists drafts, so they are left out here (PACKAGE-REPORT B-7).
// Every report is labelled AI-generated and reviewed. Report detail has no endpoint of its own (MX-13), so a
// report is read from the list; the PDF link lasts 15 minutes and the list is refreshed well before.

export type Report = components["schemas"]["ReportOut"];

const VISIBLE = new Set(["reviewed", "sent"]);

export function useReports(projectId: string) {
  return useQuery(reportsQuery(projectId));
}

/** The reports query itself, for screens that read several projects at once (useQueries). */
export function reportsQuery(projectId: string) {
  return {
    queryKey: ["project", projectId, "reports"],
    staleTime: 5 * 60_000,
    refetchInterval: 10 * 60_000,
    queryFn: async () => {
      const all = await call(
        api().GET("/api/v1/projects/{project_id}/reports", { params: { path: { project_id: projectId } } }),
      );
      return all
        .filter((r) => VISIBLE.has(r.status))
        .sort((a, b) => b.week_start.localeCompare(a.week_start));
    },
  };
}

function Labels() {
  return (
    <span className="flex flex-wrap gap-2">
      <ToneChip label="AI-generated" tone="info" size="small" />
      <ToneChip label="Reviewed by supervisor" tone="ok" size="small" />
    </span>
  );
}

export function ReportsList({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const reports = useReports(projectId);
  if (reports.isPending)
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-10">
        <Loading label="Loading the reports">
          <Skeleton className="h-40 w-full" />
        </Loading>
      </div>
    );
  if (!reports.data) return <ServerErrorContent reference={null} onRetry={() => void reports.refetch()} />;
  const items = reports.data;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-4 px-4 py-6 sm:px-10">
      <h2 className="sr-only">Weekly reports</h2>
      {items.length ? (
        <>
          <p className="text-slate">
            {items.length} {items.length === 1 ? "report" : "reports"} · also sent to you on WhatsApp and
            email
          </p>
          <ul className="flex flex-col gap-3">
            {items.map((r) => (
              <li key={r.id}>
                <Card className="flex flex-wrap items-start gap-4 p-5">
                  <div className="flex flex-1 flex-col gap-2">
                    <p className="flex flex-wrap items-baseline gap-x-3">
                      <span className="type-h3 text-ink">Week of {formatDate(r.week_start, timeZone)}</span>
                      {r.sent_at ? (
                        <span className="type-small text-slate">Sent {formatDate(r.sent_at, timeZone)}</span>
                      ) : null}
                    </p>
                    <p className="text-slate">{summaryOf(r.body_md)}</p>
                    <p className="type-small text-slate">{r.evidence_ids.length} evidence cited</p>
                    <Labels />
                  </div>
                  <Button asChild variant="outline">
                    <Link href={`/projects/${projectId}/reports/${r.id}`}>Read</Link>
                  </Button>
                </Card>
              </li>
            ))}
          </ul>
        </>
      ) : (
        <Card>
          <EmptyState icon={FileText} title="No weekly reports yet">
            A report is written every Friday once work has started, checked by your supervisor, then sent to
            you.
          </EmptyState>
        </Card>
      )}
      <p className="type-small text-slate">
        You only see reports after the supervisor has reviewed them. If a review is late, the report arrives
        late rather than unchecked.
      </p>
    </div>
  );
}

export function ReportViewer({ projectId, reportId }: { projectId: string; reportId: string }) {
  const timeZone = useViewerTimeZone();
  const reports = useReports(projectId);
  if (reports.isPending)
    return (
      <div className="mx-auto w-full max-w-4xl px-4 py-6 sm:px-10">
        <Loading label="Loading the report">
          <Skeleton className="h-96 w-full" />
        </Loading>
      </div>
    );
  if (!reports.data) return <ServerErrorContent reference={null} onRetry={() => void reports.refetch()} />;
  const r = reports.data.find((x) => x.id === reportId);
  if (!r) return <NotFoundContent />;

  return (
    <article className="mx-auto flex w-full max-w-4xl flex-col gap-5 px-4 py-6 sm:px-10">
      <Link
        href={`/projects/${projectId}/reports`}
        className="type-small self-start rounded-control font-semibold text-accent"
      >
        ‹ All reports
      </Link>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div className="flex flex-col gap-2">
          <h2 className="type-h1 text-ink">Week of {formatDate(r.week_start, timeZone)}</h2>
          <Labels />
          <p className="type-small text-slate">
            Reviewed{r.sent_at ? ` and sent ${formatDateTime(r.sent_at, timeZone)}` : ""}.
          </p>
        </div>
        {r.pdf_url ? (
          <Button asChild variant="outline">
            <a href={r.pdf_url} target="_blank" rel="noreferrer">
              <Download aria-hidden strokeWidth={1.75} className="size-4" />
              Download PDF
            </a>
          </Button>
        ) : null}
      </div>
      <p className="type-small flex items-start gap-3 rounded-card bg-mist p-4 text-slate">
        <Sparkles aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
        Written by iBackHome&apos;s AI report assistant from this week&apos;s evidence, the supervisor&apos;s
        notes and the ledger, then checked by your supervisor. It reports facts only. It can&apos;t approve
        anything or move money.
      </p>
      <Card className="p-6">
        <Markdown source={r.body_md} />
      </Card>
      {r.evidence_ids.length ? (
        <section className="flex flex-col gap-2">
          <h3 className="type-h3 text-ink">Evidence cited</h3>
          <p className="flex flex-wrap gap-2">
            {r.evidence_ids.map((id) => (
              <span key={id} className="type-mono rounded-tag border border-line bg-mist px-1.5 text-ink">
                EV-{shortId(id)}
              </span>
            ))}
          </p>
          <Link
            href={`/projects/${projectId}/evidence`}
            className="type-small self-start rounded-control font-semibold text-accent"
          >
            Open the evidence gallery ›
          </Link>
        </section>
      ) : null}
    </article>
  );
}
