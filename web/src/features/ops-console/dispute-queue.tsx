"use client";

import { useQueries } from "@tanstack/react-query";
import { Info, Scale } from "lucide-react";
import Link from "next/link";

import { api, call } from "@/common/api/client";
import { keys, useProjects, type Milestone } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { disputeRef, queueChip } from "./disputes";
import { useOpsQueue } from "./queries";

// WEB-OPS-006 frame 1: the open disputes from GET /ops/queue, with project and milestone names and the money
// held. The "Resolved" tab needs a dispute list (MX-10) and the design's "[2 business days]" target is a
// placeholder, so neither is shown. Only the client can raise a dispute (backend), so "Raised by" says Client.

export function DisputeQueue({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const queue = useOpsQueue();
  const projects = useProjects();
  const projectIds = [...new Set((queue.data?.disputes ?? []).map((d) => d.project_id))];
  const milestones = useQueries({
    queries: projectIds.map((id) => ({
      queryKey: keys.milestones(id),
      queryFn: () =>
        call(api().GET("/api/v1/projects/{project_id}/milestones", { params: { path: { project_id: id } } })),
    })),
  });

  const header = <OpsHeader title="Disputes" environment={environment} />;
  if (queue.isPending || projects.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the disputes">
            <Skeleton className="h-32 w-full" />
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

  const titles = new Map((projects.data?.items ?? []).map((p) => [p.id, p.title]));
  const byId = new Map<string, Milestone>();
  for (const q of milestones) for (const m of (q.data ?? []) as Milestone[]) byId.set(m.id, m);
  const disputes = [...queue.data.disputes].sort((a, b) => a.opened_at.localeCompare(b.opened_at));

  return (
    <>
      {header}
      <div className="flex flex-col gap-4 p-5">
        <p className="type-small text-slate">
          Open {disputes.length} · While a dispute is open, no release can be requested for that milestone.
        </p>
        {disputes.length ? (
          <Table caption="Open disputes" dense>
            <thead>
              <tr>
                <Th>Dispute</Th>
                <Th>Project · milestone</Th>
                <Th>Raised by</Th>
                <Th numeric>Held</Th>
                <Th>Opened</Th>
                <Th>Status</Th>
              </tr>
            </thead>
            <tbody>
              {disputes.map((d) => {
                const m = byId.get(d.milestone_id);
                const chip = queueChip(d);
                return (
                  <Tr key={d.dispute_id}>
                    <Td>
                      <Link
                        href={`/ops/disputes/${d.dispute_id}`}
                        className="type-mono rounded-control font-semibold text-ink underline"
                      >
                        {disputeRef(d.dispute_id)}
                      </Link>
                    </Td>
                    <Td>
                      {titles.get(d.project_id) ?? "Project"} · {m?.name ?? "Milestone"}
                    </Td>
                    <Td>Client</Td>
                    <Td numeric>{m ? formatMoney(m.amount_minor, "NGN") : "–"}</Td>
                    <Td>{formatDateTime(d.opened_at, timeZone)}</Td>
                    <Td>
                      <ToneChip label={chip.label} tone={chip.tone} size="small" />
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        ) : (
          <EmptyState icon={Scale} title="No open disputes">
            When a client disputes a milestone, it shows here.
          </EmptyState>
        )}
        <p className="type-small flex items-center gap-2 text-slate">
          <Info aria-hidden strokeWidth={1.75} className="size-4" />
          Held by a licensed escrow partner, never by iBackHome.
        </p>
        <Card className="flex flex-col gap-1.5 p-4">
          <CardLabel>Resolution rules</CardLabel>
          <p className="type-small text-slate">
            Two different ops people must agree on the outcome, release or rework. One proposes, a second
            approves, and nobody can approve their own proposal. Every step goes in the audit log.
          </p>
        </Card>
      </div>
    </>
  );
}
