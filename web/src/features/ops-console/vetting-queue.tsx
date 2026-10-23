"use client";

import { ShieldCheck } from "lucide-react";
import Link from "next/link";

import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { waited } from "./ops";
import { useOpsQueue } from "./queries";

// WEB-OPS-003 Vetting queue at /ops/vetting: the applications from GET /ops/queue, oldest first; each opens the
// application and the decision (/ops/vetting/:id, W8b).

export function VettingQueue({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const queue = useOpsQueue();
  const header = <OpsHeader title="Vetting" environment={environment} />;
  if (queue.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the vetting queue">
            <Skeleton className="h-48 w-full" />
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
  const items = [...queue.data.vetting].sort((a, b) => a.submitted_at.localeCompare(b.submitted_at));
  return (
    <>
      {header}
      <div className="flex flex-col gap-4 p-5">
        <p className="type-small text-slate">
          Approving a supervisor needs their registration, NIN and both guarantors checked. Open an
          application to check and decide.
        </p>
        {items.length ? (
          <Table caption="Supervisor applications" dense>
            <thead>
              <tr>
                <Th>Applicant</Th>
                <Th>Registration</Th>
                <Th>Submitted</Th>
                <Th>Waiting</Th>
              </tr>
            </thead>
            <tbody>
              {items.map((v) => (
                <Tr key={v.user_id}>
                  <Td>
                    <Link
                      href={`/ops/vetting/${v.user_id}`}
                      className="type-mono font-semibold text-ink underline"
                    >
                      Application {shortId(v.user_id)}
                    </Link>
                  </Td>
                  <Td>
                    {v.registration_body} · <span className="type-mono">{v.registration_no}</span>
                  </Td>
                  <Td>{formatDateTime(v.submitted_at, timeZone)}</Td>
                  <Td>{waited(v.submitted_at)}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <Card>
            <EmptyState icon={ShieldCheck} title="No applications waiting">
              Supervisors apply in the iBackHome app.
            </EmptyState>
          </Card>
        )}
      </div>
    </>
  );
}
