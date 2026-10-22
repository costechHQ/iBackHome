"use client";

import { useQueries, useQueryClient } from "@tanstack/react-query";
import { FileText, Info } from "lucide-react";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { shortId, useProjects } from "@/common/api/queries";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDate, formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Markdown } from "@/common/ui/markdown";
import { ConfirmDialog } from "@/common/ui/dialog";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

// WEB-OPS-010 Weekly reports at /ops/reports: every project's reports (read project by project; there's no
// list across projects, MX-13), drafts first, and one report with "Mark reviewed and send"
// (POST /reports/{id}/review: the PDF is made and the report is queued to the client). The backend lets ops
// review any draft. Not built (PACKAGE-REPORT W-45): the ops edit, "Regenerate draft", the reviewer's name,
// "2 days late" and the runs summary (no endpoints; agent runs need MX-18).

type Report = components["schemas"]["ReportOut"];

const STATUS: Record<string, { label: string; tone: "warn" | "ok" | "neutral" }> = {
  draft: { label: "Draft · not reviewed", tone: "warn" },
  reviewed: { label: "Reviewed", tone: "ok" },
  sent: { label: "Sent", tone: "ok" },
};
const ORDER: Record<string, number> = { draft: 0, reviewed: 1, sent: 2 };

function useAllReports() {
  const projects = useProjects();
  const items = projects.data?.items ?? [];
  const reports = useQueries({
    queries: items.map((p) => ({
      queryKey: ["ops", "reports", p.id],
      queryFn: () =>
        call(api().GET("/api/v1/projects/{project_id}/reports", { params: { path: { project_id: p.id } } })),
    })),
  });
  const titles = new Map(items.map((p) => [p.id, p.title]));
  const all = reports
    .flatMap((q) => q.data ?? [])
    .sort(
      (a, b) =>
        (ORDER[a.status] ?? 9) - (ORDER[b.status] ?? 9) ||
        b.week_start.localeCompare(a.week_start) ||
        (titles.get(a.project_id) ?? "").localeCompare(titles.get(b.project_id) ?? ""),
    );
  return {
    all,
    titles,
    isPending: projects.isPending || reports.some((q) => q.isPending),
    error: projects.error ?? reports.find((q) => q.error)?.error ?? null,
    refetch: () => {
      void projects.refetch();
      reports.forEach((q) => void q.refetch());
    },
  };
}

function Review({ report, title }: { report: Report; title: string }) {
  const timeZone = useViewerTimeZone();
  const queries = useQueryClient();
  const [confirm, setConfirm] = useState(false);
  const review = useWrite(
    (_: null, key: string) =>
      call(
        api().POST("/api/v1/reports/{report_id}/review", {
          params: { path: { report_id: report.id } },
          headers: { "Idempotency-Key": key },
        }),
      ),
    { onSettled: () => void queries.invalidateQueries({ queryKey: ["ops", "reports", report.project_id] }) },
  );
  const status = STATUS[report.status] ?? { label: report.status, tone: "neutral" as const };
  const failure = review.error instanceof ApiError ? review.error : null;
  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="type-h3 text-ink">
          {title} · week of {formatDate(report.week_start, timeZone)}
        </h2>
        <span className="flex flex-wrap gap-2">
          <ToneChip label="AI-generated" tone="info" size="small" />
          <ToneChip label={status.label} tone={status.tone} size="small" />
        </span>
      </div>
      {failure?.status === 409 ? (
        <Alert tone="info" title="Already reviewed">
          The supervisor or another ops person reviewed it first.
        </Alert>
      ) : failure?.code === "pdf_unavailable" ? (
        <Alert tone="warn" title="The PDF couldn’t be made">
          Nothing was sent. Try again in a minute.
        </Alert>
      ) : review.error ? (
        <Alert tone="bad" title="The review wasn’t saved">
          Try again.
        </Alert>
      ) : null}
      <div className="max-h-150 overflow-y-auto rounded-control border border-line p-4">
        <Markdown source={report.body_md} />
      </div>
      <p className="type-small text-slate">
        Based on {report.evidence_ids.length} {report.evidence_ids.length === 1 ? "capture" : "captures"}
        {report.evidence_ids.length
          ? `: ${report.evidence_ids
              .slice(0, 6)
              .map((id) => `EV-${shortId(id)}`)
              .join(", ")}${report.evidence_ids.length > 6 ? "…" : ""}`
          : ""}
        . Money figures come from the ledger, never from the AI.
      </p>
      {report.status === "draft" ? (
        <div className="flex flex-col gap-2">
          <Button className="self-start" onClick={() => setConfirm(true)} loading={review.isPending}>
            Mark reviewed and send
          </Button>
          <p className="type-small text-slate">
            The PDF is made and the report goes to the client by WhatsApp and email.
          </p>
        </div>
      ) : (
        <p className="type-small text-slate">
          {report.sent_at
            ? `Sent ${formatDateTime(report.sent_at, timeZone)}.`
            : "Reviewed; waiting to be sent."}
        </p>
      )}
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Send this report to the client?"
        description="You confirm it matches the evidence and the ledger. The client gets it by WhatsApp and email, marked as reviewed."
        confirmLabel="Mark reviewed and send"
        cancelLabel="Keep reading"
        busy={review.isPending}
        onConfirm={() => review.mutate(null, { onSettled: () => setConfirm(false) })}
      />
    </Card>
  );
}

export function ReportsReview({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const data = useAllReports();
  const [selected, setSelected] = useState<string | null>(null);
  const header = <OpsHeader title="Weekly reports" environment={environment} />;

  if (data.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the reports">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (data.error) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={data.refetch} />
      </>
    );
  }
  const current =
    data.all.find((r) => r.id === selected) ?? data.all.find((r) => r.status === "draft") ?? null;
  const drafts = data.all.filter((r) => r.status === "draft").length;

  return (
    <>
      {header}
      <div className="grid gap-5 p-5 lg:grid-cols-2">
        <div className="flex flex-col gap-4">
          <p className="type-small flex items-start gap-2 text-slate">
            <Info aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
            {drafts} {drafts === 1 ? "draft waits" : "drafts wait"} for review. The supervisor normally
            reviews; ops can review any draft, for example when it’s late or the supervisor is part of a
            dispute.
          </p>
          {data.all.length ? (
            <Table caption="Weekly reports" dense>
              <thead>
                <tr>
                  <Th>Project</Th>
                  <Th>Week of</Th>
                  <Th>Status</Th>
                  <Th>Sent</Th>
                </tr>
              </thead>
              <tbody>
                {data.all.map((r) => {
                  const s = STATUS[r.status] ?? { label: r.status, tone: "neutral" as const };
                  const active = current?.id === r.id;
                  return (
                    <Tr key={r.id} className={cn(active && "bg-mist")}>
                      <Td>
                        <button
                          type="button"
                          aria-pressed={active}
                          onClick={() => setSelected(r.id)}
                          className="text-left font-semibold text-ink underline"
                        >
                          {data.titles.get(r.project_id) ?? "Project"}
                        </button>
                      </Td>
                      <Td>{formatDate(r.week_start, timeZone)}</Td>
                      <Td>
                        <ToneChip label={s.label} tone={s.tone} size="small" />
                      </Td>
                      <Td>{r.sent_at ? formatDateTime(r.sent_at, timeZone) : "–"}</Td>
                    </Tr>
                  );
                })}
              </tbody>
            </Table>
          ) : (
            <Card>
              <EmptyState icon={FileText} title="No weekly reports yet">
                The report agent drafts one for each active project every Friday at 16:00 WAT.
              </EmptyState>
            </Card>
          )}
        </div>
        {current ? (
          <Review
            key={current.id}
            report={current}
            title={data.titles.get(current.project_id) ?? "Project"}
          />
        ) : null}
      </div>
    </>
  );
}
