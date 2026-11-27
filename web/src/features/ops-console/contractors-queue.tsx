"use client";

import { HardHat } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { formatDateTime } from "@/common/time";
import { SelectField } from "@/common/ui/field";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { useContractorApplications, useContractorDirectory, type ApplicationStatus } from "./contractors-api";
import { listText, SPECIALTY_LABELS, specialtyLabel } from "./contractors";
import { waited } from "./ops";

// Contractors at /ops/contractors (ADR 0007, phase 1): the applications ops vet (oldest first; each opens the
// application and the decision at /ops/contractors/:id) and the directory of approved contractors that ops
// will shortlist from when a client asks for a match (phase 2). Phone numbers and emails are not in the lists.

type View = "applications" | "directory";

const STATUS_OPTIONS: { value: ApplicationStatus; label: string }[] = [
  { value: "pending", label: "Waiting for ops" },
  { value: "approved", label: "Approved" },
  { value: "rejected", label: "Rejected" },
];

function Waiting() {
  return (
    <div className="p-5">
      <Loading label="Loading contractors">
        <Skeleton className="h-48 w-full" />
      </Loading>
    </div>
  );
}

function Applications() {
  const timeZone = useViewerTimeZone();
  const [status, setStatus] = useState<ApplicationStatus>("pending");
  const list = useContractorApplications(status);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="type-small max-w-2xl text-slate">
          Approving a contractor needs both references called, and their registration checked if they gave a
          CAC or CORBON number. You write the profile summary clients will read.
        </p>
        <SelectField
          label="Show"
          value={status}
          onChange={(e) => setStatus(e.target.value as ApplicationStatus)}
          className="w-52"
        >
          {STATUS_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </SelectField>
      </div>
      {list.isPending ? (
        <Waiting />
      ) : !list.data ? (
        <ServerErrorContent reference={null} onRetry={() => void list.refetch()} />
      ) : list.data.items.length ? (
        <Table caption="Contractor applications" dense>
          <thead>
            <tr>
              <Th>Business</Th>
              <Th>Contact</Th>
              <Th>States</Th>
              <Th>Applied</Th>
              <Th>{status === "pending" ? "Waiting" : "Status"}</Th>
            </tr>
          </thead>
          <tbody>
            {list.data.items.map((a) => (
              <Tr key={a.id}>
                <Td>
                  <Link href={`/ops/contractors/${a.id}`} className="font-semibold text-ink underline">
                    {a.business_name}
                  </Link>{" "}
                  <span className="type-mono text-muted">{shortId(a.id)}</span>
                </Td>
                <Td>{a.contact_name}</Td>
                <Td>{listText(a.states_served)}</Td>
                <Td>{formatDateTime(a.created_at, timeZone)}</Td>
                <Td>{status === "pending" ? waited(a.created_at) : a.status}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <Card>
          <EmptyState
            icon={HardHat}
            title={status === "pending" ? "No applications waiting" : "None here yet"}
          >
            Contractors apply on the Contractors page of the website.
          </EmptyState>
        </Card>
      )}
    </div>
  );
}

function Directory() {
  const timeZone = useViewerTimeZone();
  const [state, setState] = useState("");
  const [specialty, setSpecialty] = useState("");
  const list = useContractorDirectory(state, specialty);
  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-end gap-3">
        <SelectField label="State" value={state} onChange={(e) => setState(e.target.value)} className="w-52">
          <option value="">Any state</option>
          {NIGERIAN_STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </SelectField>
        <SelectField
          label="Kind of work"
          value={specialty}
          onChange={(e) => setSpecialty(e.target.value)}
          className="w-52"
        >
          <option value="">Any kind</option>
          {Object.entries(SPECIALTY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </SelectField>
      </div>
      {list.isPending ? (
        <Waiting />
      ) : !list.data ? (
        <ServerErrorContent reference={null} onRetry={() => void list.refetch()} />
      ) : list.data.items.length ? (
        <Table caption="Approved contractors" dense>
          <thead>
            <tr>
              <Th>Business</Th>
              <Th>States</Th>
              <Th>Kinds of work</Th>
              <Th>Years</Th>
              <Th>Projects</Th>
              <Th>Approved</Th>
            </tr>
          </thead>
          <tbody>
            {list.data.items.map((c) => (
              <Tr key={c.id}>
                <Td>
                  <span className="font-semibold text-ink">{c.business_name}</span>
                  {!c.listed ? <span className="type-small text-muted"> (not listed)</span> : null}
                </Td>
                <Td>{listText(c.states_served)}</Td>
                <Td>{listText(c.specialties, specialtyLabel)}</Td>
                <Td>{c.years_in_business}</Td>
                <Td>{c.projects_completed}</Td>
                <Td>{formatDateTime(c.vetted_at, timeZone)}</Td>
              </Tr>
            ))}
          </tbody>
        </Table>
      ) : (
        <Card>
          <EmptyState icon={HardHat} title="No approved contractors match">
            Approve an application to add a contractor to the directory.
          </EmptyState>
        </Card>
      )}
    </div>
  );
}

export function ContractorsQueue({ environment }: { environment: string }) {
  const [view, setView] = useState<View>("applications");
  return (
    <>
      <OpsHeader title="Contractors" environment={environment} />
      <div className="flex flex-col gap-4 p-5">
        <SegmentedControl<View>
          label="Contractors view"
          value={view}
          onChange={setView}
          segments={[
            { value: "applications", label: "Applications" },
            { value: "directory", label: "Directory" },
          ]}
        />
        {view === "applications" ? <Applications /> : <Directory />}
      </div>
    </>
  );
}
