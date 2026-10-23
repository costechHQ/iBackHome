"use client";

import { ShieldCheck } from "lucide-react";

import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { waited } from "./ops";
import { useOpsQueue } from "./queries";

// WEB-OPS-003 Vetting, the queue only (/ops/vetting): the applications from GET /ops/queue, oldest first. The
// application detail and the decision need the applicant's name, phone and guarantors, which ops can't read
// yet (MX-15; PACKAGE-REPORT W-48): approving means confirming the guarantors, so no decision is offered here.

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
        <Alert tone="info" title="Reviewing an application needs its full details">
          Approving a supervisor means confirming their registration, NIN and both guarantors. The
          application’s contacts and guarantors can’t be shown here yet, so applications are listed but not
          decided from this page.
        </Alert>
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
                  <Td className="type-mono">{shortId(v.user_id)}</Td>
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
