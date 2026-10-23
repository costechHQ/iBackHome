"use client";

import { FolderSearch } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { useOpsProjects } from "./data";
import { PROJECT_TABS } from "./ops";

// WEB-OPS-004 Projects list at /ops/projects: every project, by status, searchable by title or address, with
// what is happening now and what needs ops. Client, contractor and supervisor names need MX-26, so the list
// says whether each is set (PACKAGE-REPORT W-43).

type TabKey = (typeof PROJECT_TABS)[number]["key"];

export function OpsProjects({ environment }: { environment: string }) {
  const data = useOpsProjects();
  const [tab, setTab] = useState<TabKey>("all");
  const [search, setSearch] = useState("");
  const searchId = useId();
  const header = <OpsHeader title="Projects" environment={environment} />;

  if (data.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the projects">
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

  const term = search.trim().toLowerCase();
  const matchTab = PROJECT_TABS.find((t) => t.key === tab)!.match;
  const rows = data.rows
    .filter((r) => matchTab(r.project.status))
    .filter(
      (r) =>
        !term ||
        r.project.title.toLowerCase().includes(term) ||
        r.project.address.toLowerCase().includes(term),
    )
    .sort((a, b) => b.flags.length - a.flags.length || a.project.title.localeCompare(b.project.title));

  return (
    <>
      {header}
      <div className="flex flex-col gap-4 p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <SegmentedControl
            label="Project status"
            value={tab}
            onChange={setTab}
            segments={PROJECT_TABS.map((t) => ({
              value: t.key,
              label: t.label,
              count: data.rows.filter((r) => t.match(r.project.status)).length,
            }))}
          />
          <div className="flex items-center gap-2">
            <label htmlFor={searchId} className="type-small font-semibold text-ink">
              Search
            </label>
            <input
              id={searchId}
              type="search"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Title or address"
              className="min-h-target w-72 rounded-control border border-line-strong bg-white px-3 text-ink"
            />
          </div>
        </div>
        {rows.length ? (
          <Table caption="Projects" dense>
            <thead>
              <tr>
                <Th>Project</Th>
                <Th>Contractor</Th>
                <Th>Supervisor</Th>
                <Th>Now</Th>
                <Th>Status</Th>
                <Th>Needs</Th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <Tr key={r.project.id}>
                  <Td>
                    <Link href={`/ops/projects/${r.project.id}`} className="font-semibold text-ink underline">
                      {r.project.title}
                    </Link>
                    <span className="block text-slate">{r.project.address}</span>
                  </Td>
                  <Td>{r.project.contractor_id ? "Added" : "–"}</Td>
                  <Td>{r.project.supervisor_id ? "Assigned" : "–"}</Td>
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
          <EmptyState icon={FolderSearch} title="No projects match">
            Try another status or search.
          </EmptyState>
        )}
      </div>
    </>
  );
}
