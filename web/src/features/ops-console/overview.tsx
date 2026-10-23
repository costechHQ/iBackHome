"use client";

import { CircleCheck, Flag, Scale, ShieldCheck } from "lucide-react";
import Link from "next/link";

import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { useOpsProjects } from "./data";
import { oldest, waited } from "./ops";
import { useOpsQueue } from "./queries";

// WEB-OPS-002 Overview at /ops: the three queues with how long the oldest item has waited, the projects by
// status, and the projects that need ops (their BoQ waits for the ops approval, no supervisor, a dispute).
// Not shown (PACKAGE-REPORT W-42): failed releases, reconciliation mismatches and the alerts panel (MX-21), the
// live map of every site (the project list doesn't carry the sites), "Today on site" (MX-24), the search box.

function QueueTile({
  href,
  label,
  count,
  since,
  icon: Icon,
}: {
  href: string;
  label: string;
  count: number;
  since: string | null;
  icon: typeof Flag;
}) {
  return (
    <Link href={href} className="block rounded-card hover:shadow-raised">
      <Card className="flex h-full flex-col gap-1 p-4">
        <p className="type-small flex items-center gap-2 text-slate">
          <Icon aria-hidden strokeWidth={1.75} className="size-4" />
          {label}
        </p>
        <p className="ibh-tabular type-h1 text-ink">{count}</p>
        <p className="type-small text-slate">{since ? `Oldest ${waited(since)}` : "Nothing waiting"}</p>
      </Card>
    </Link>
  );
}

export function OpsOverview({ environment }: { environment: string }) {
  const queue = useOpsQueue();
  const projects = useOpsProjects();
  const header = <OpsHeader title="Overview" environment={environment} />;

  if (queue.isPending || projects.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the overview">
            <Skeleton className="h-24 w-full" />
            <Skeleton className="h-64 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (!queue.data || projects.error) {
    return (
      <>
        {header}
        <ServerErrorContent
          reference={null}
          onRetry={() => {
            void queue.refetch();
            projects.refetch();
          }}
        />
      </>
    );
  }

  const q = queue.data;
  const waitingSecond = q.disputes.filter((d) => d.proposed_outcome).length;
  const needing = projects.rows.filter((r) => r.flags.length);
  const byStatus = ["draft", "boq_review", "active", "paused", "completed"].map((s) => ({
    status: s,
    count: projects.rows.filter((r) => r.project.status === s).length,
  }));

  return (
    <>
      {header}
      <div className="flex flex-col gap-5 p-5">
        <div className="grid gap-4 lg:grid-cols-4">
          <QueueTile
            href="/ops/vetting"
            label="Vetting"
            icon={ShieldCheck}
            count={q.vetting.length}
            since={oldest(q.vetting.map((v) => v.submitted_at))}
          />
          <QueueTile
            href="/ops/evidence"
            label="Flagged evidence"
            icon={Flag}
            count={q.flagged_evidence.length}
            since={oldest(q.flagged_evidence.map((e) => e.flagged_at))}
          />
          <Link href="/ops/disputes" className="block rounded-card hover:shadow-raised">
            <Card className="flex h-full flex-col gap-1 p-4">
              <p className="type-small flex items-center gap-2 text-slate">
                <Scale aria-hidden strokeWidth={1.75} className="size-4" />
                Disputes
              </p>
              <p className="ibh-tabular type-h1 text-ink">{q.disputes.length}</p>
              <p className="type-small text-slate">
                {waitingSecond
                  ? `${waitingSecond} waiting for a second approver`
                  : q.disputes.length
                    ? `Oldest ${waited(oldest(q.disputes.map((d) => d.opened_at))!)}`
                    : "Nothing waiting"}
              </p>
            </Card>
          </Link>
          <Card className="flex flex-col gap-2 p-4">
            <CardLabel>Projects</CardLabel>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1">
              {byStatus.map((s) => (
                <div key={s.status} className="flex items-center justify-between gap-2">
                  <dt>
                    <StatusChip entity="project" state={s.status} audience="ops" size="small" />
                  </dt>
                  <dd className="ibh-tabular font-semibold text-ink">{s.count}</dd>
                </div>
              ))}
            </dl>
          </Card>
        </div>

        <Card className="overflow-hidden">
          <h2 className="border-b border-line px-4 py-3 font-semibold text-ink">
            Projects that need ops · {needing.length}
          </h2>
          {needing.length ? (
            <Table caption="Projects that need ops" dense className="rounded-none border-0">
              <thead>
                <tr>
                  <Th>Project</Th>
                  <Th>Now</Th>
                  <Th>Status</Th>
                  <Th>Needs</Th>
                </tr>
              </thead>
              <tbody>
                {needing.map((r) => (
                  <Tr key={r.project.id}>
                    <Td>
                      <Link
                        href={`/ops/projects/${r.project.id}`}
                        className="font-semibold text-ink underline"
                      >
                        {r.project.title}
                      </Link>
                    </Td>
                    <Td>{r.now}</Td>
                    <Td>
                      <StatusChip entity="project" state={r.project.status} audience="ops" size="small" />
                    </Td>
                    <Td>
                      <span className="flex flex-wrap gap-1.5">
                        {r.flags.map((f) => (
                          <ToneChip key={f.label} label={f.label} tone={f.tone} size="small" />
                        ))}
                      </span>
                    </Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <EmptyState icon={CircleCheck} title="Nothing needs ops on any project" />
          )}
        </Card>
      </div>
    </>
  );
}
