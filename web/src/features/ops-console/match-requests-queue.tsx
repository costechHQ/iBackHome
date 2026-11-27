"use client";

import { Handshake } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { SelectField } from "@/common/ui/field";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { specialtyLabel } from "./contractors";
import { MATCH_STATUS, type MatchStatus } from "./matching";
import { useMatchRequests } from "./matching-api";
import { waited } from "./ops";

// Match requests at /ops/match-requests (ADR 0007, phase 2): clients who asked us to find them a contractor,
// oldest first. Each opens the request and the shortlist builder (/ops/match-requests/:projectId). The usual
// work: phone the contractors you would put forward, then set a shortlist of 1 to 3 for the client.

const OPTIONS: MatchStatus[] = ["open", "shortlisted", "matched", "cancelled"];

export function MatchRequestsQueue({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const [status, setStatus] = useState<MatchStatus>("open");
  const list = useMatchRequests(status);
  return (
    <>
      <OpsHeader title="Match requests" environment={environment} />
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <p className="type-small max-w-2xl text-slate">
            Phone each contractor you would put forward and check they are free and interested, then set a
            shortlist of one to three. The client is told and chooses.
          </p>
          <SelectField
            label="Show"
            value={status}
            onChange={(e) => setStatus(e.target.value as MatchStatus)}
            className="w-52"
          >
            {OPTIONS.map((s) => (
              <option key={s} value={s}>
                {MATCH_STATUS[s].label}
              </option>
            ))}
          </SelectField>
        </div>
        {list.isPending ? (
          <div className="p-5">
            <Loading label="Loading match requests">
              <Skeleton className="h-48 w-full" />
            </Loading>
          </div>
        ) : !list.data ? (
          <ServerErrorContent reference={null} onRetry={() => void list.refetch()} />
        ) : list.data.items.length ? (
          <Table caption="Match requests" dense>
            <thead>
              <tr>
                <Th>Project</Th>
                <Th>Where</Th>
                <Th>Kind of work</Th>
                <Th>Budget</Th>
                <Th>Asked</Th>
                <Th>{status === "open" ? "Waiting" : "Shortlist"}</Th>
              </tr>
            </thead>
            <tbody>
              {list.data.items.map((r) => (
                <Tr key={r.id}>
                  <Td>
                    <Link
                      href={`/ops/match-requests/${r.project_id}`}
                      className="font-semibold text-ink underline"
                    >
                      {r.project_title}
                    </Link>
                  </Td>
                  <Td>
                    {r.city}, {r.state}
                  </Td>
                  <Td>{specialtyLabel(r.work_type)}</Td>
                  <Td>{formatMoney(r.budget_minor, r.currency)}</Td>
                  <Td>{formatDateTime(r.created_at, timeZone)}</Td>
                  <Td>{status === "open" ? waited(r.created_at) : `${r.shortlist_count} contractor(s)`}</Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        ) : (
          <Card>
            <EmptyState icon={Handshake} title={status === "open" ? "No requests waiting" : "None here yet"}>
              Clients ask for a contractor from their project&apos;s set-up page.
            </EmptyState>
          </Card>
        )}
      </div>
    </>
  );
}
