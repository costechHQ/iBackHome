"use client";

import { CircleCheck, Info, Pencil } from "lucide-react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useMilestones, useProject } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { fromGeoJson } from "@/common/map/geo";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip, ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";
import { heldMinor } from "@/features/milestones/contractor";
import { useApproveBoq, useBoq } from "@/features/projects/api";
import { SavedLines } from "@/features/projects/boq-editor";

import { ProjectSpotChecks, SupervisorPicker } from "./supervisor-picker";

// WEB-OPS-004 Project detail at /ops/projects/:id: milestones and the money held, the site boundary with
// "Change site" (ops may change it at any time; every change is audited), the BoQ with the ops approval, and
// the supervisor (choose or change one) and the spot checks (W8b, supervisor-picker.tsx). Not shown
// (PACKAGE-REPORT W-43): "Pause project" (MX-09), client and contractor names (MX-26).

const GeofenceMap = dynamic(() => import("@/common/map/geofence-map").then((m) => m.GeofenceMap), {
  ssr: false,
  loading: () => <Skeleton className="h-full w-full" />,
});

const ROLES = [
  { role: "contractor", name: "Contractor" },
  { role: "client", name: "Client" },
  { role: "ops", name: "iBackHome ops" },
];

function BoqCard({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const boq = useBoq(projectId);
  const approve = useApproveBoq(projectId);
  const [confirm, setConfirm] = useState(false);
  const [open, setOpen] = useState(false);
  if (boq.isPending) return <Skeleton className="h-40 w-full" />;
  if (!boq.data) return null;
  const b = boq.data;
  const opsMissing = b.project_status === "boq_review" && b.approvals_missing.includes("ops");
  const others = b.approvals_missing.filter((r) => r !== "ops");
  const failure = approve.error instanceof ApiError ? approve.error.code : approve.error ? "error" : null;
  return (
    <Card className="flex flex-col gap-4 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-semibold text-ink">Bill of quantities</h2>
        {b.milestones.length ? (
          <p className="ibh-tabular type-small text-slate">
            Lines total{" "}
            <span className="font-semibold text-ink">{formatMoney(b.boq_total_minor, "NGN")}</span> · budget{" "}
            {formatMoney(b.budget_minor, "NGN")}
          </p>
        ) : null}
      </div>
      {b.milestones.length === 0 ? (
        <p className="type-small text-slate">The contractor hasn’t submitted a BoQ yet.</p>
      ) : (
        <>
          <ul className="flex flex-col gap-1.5">
            {ROLES.map(({ role, name }) => {
              const a = b.approvals.find((x) => x.role === role);
              return (
                <li key={role} className="type-small flex items-center justify-between gap-3">
                  <span className="text-ink">{name}</span>
                  {a ? (
                    <span className="flex items-center gap-1.5 text-ok-fg">
                      <CircleCheck aria-hidden strokeWidth={1.75} className="size-4" />
                      Approved {formatDateTime(a.approved_at, timeZone)}
                    </span>
                  ) : (
                    <ToneChip label="Waiting" tone="neutral" size="small" />
                  )}
                </li>
              );
            })}
          </ul>
          {failure === "site_not_set" ? (
            <Alert tone="warn" title="The site isn’t set">
              The last approval makes the project live, so the site and its boundary must be saved first.
            </Alert>
          ) : failure ? (
            <Alert tone="bad" title="The approval wasn’t saved">
              Try again.
            </Alert>
          ) : null}
          <div className="flex flex-wrap gap-3">
            {opsMissing ? (
              <Button onClick={() => setConfirm(true)} loading={approve.isPending}>
                Approve BoQ as ops
              </Button>
            ) : null}
            <Button variant="secondary" aria-expanded={open} onClick={() => setOpen(!open)}>
              {open ? "Hide the lines" : "Show the lines"}
            </Button>
          </div>
          {open ? <SavedLines boq={b} /> : null}
          <ConfirmDialog
            open={confirm}
            onOpenChange={setConfirm}
            title="Approve this BoQ?"
            description={
              others.length
                ? `Ops approves the lines against the price index and the budget. The ${others.join(" and ")} still need to approve.`
                : "This is the last approval: the project goes live and its milestones are created, ready for the client to fund."
            }
            confirmLabel="Approve BoQ"
            cancelLabel="Not yet"
            busy={approve.isPending}
            onConfirm={() => approve.mutate(null, { onSettled: () => setConfirm(false) })}
          />
        </>
      )}
    </Card>
  );
}

export function OpsProjectDetail({ projectId, environment }: { projectId: string; environment: string }) {
  const project = useProject(projectId);
  const milestones = useMilestones(projectId);

  if (project.isPending || milestones.isPending) {
    return (
      <>
        <OpsHeader title="Project" environment={environment} />
        <div className="p-5">
          <Loading label="Loading the project">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (project.error instanceof ApiError && project.error.status === 404) return <NotFoundContent />;
  if (!project.data) {
    return (
      <>
        <OpsHeader title="Project" environment={environment} />
        <ServerErrorContent reference={null} onRetry={() => void project.refetch()} />
      </>
    );
  }

  const p = project.data;
  const ms = [...(milestones.data ?? [])].sort((a, b) => a.sequence - b.sequence);
  const released = ms.filter((m) => m.status === "released").length;
  const held = heldMinor(ms);
  const corners = p.site ? fromGeoJson(p.site.geofence) : [];
  const pin = p.site ? { lat: p.site.location.lat, lon: p.site.location.lon } : null;

  return (
    <>
      <OpsHeader title={p.title} environment={environment} />
      <div className="flex flex-col gap-5 p-5">
        <div className="flex flex-wrap items-center gap-3">
          <Link href="/ops/projects" className="type-small font-semibold text-accent">
            ‹ Projects
          </Link>
          <StatusChip entity="project" state={p.status} audience="ops" size="small" />
          <p className="type-small text-slate">
            {p.address} · budget {formatMoney(p.budget_minor, "NGN")}
            {ms.length ? ` · ${released} of ${ms.length} released` : ""}
          </p>
        </div>

        <div className="grid gap-5 lg:grid-cols-5">
          <div className="flex flex-col gap-5 lg:col-span-3">
            <Card className="overflow-hidden">
              <h2 className="border-b border-line px-4 py-3 font-semibold text-ink">Milestones</h2>
              {ms.length ? (
                <>
                  <Table caption="Milestones" dense className="rounded-none border-0">
                    <thead>
                      <tr>
                        <Th>Milestone</Th>
                        <Th numeric>NGN</Th>
                        <Th>State</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {ms.map((m) => (
                        <Tr key={m.id}>
                          <Td>
                            {m.sequence} · {m.name}
                          </Td>
                          <Td numeric>{formatMoney(m.amount_minor, "NGN")}</Td>
                          <Td>
                            <StatusChip entity="milestone" state={m.status} audience="ops" size="small" />
                          </Td>
                        </Tr>
                      ))}
                    </tbody>
                  </Table>
                  <p className="type-small flex items-center gap-2 border-t border-line px-4 py-3 text-slate">
                    <Info aria-hidden strokeWidth={1.75} className="size-4 flex-none" />
                    {ESCROW_LINE} {formatMoney(held, "NGN")} held now.
                  </p>
                </>
              ) : (
                <p className="type-small px-4 py-3 text-slate">
                  Milestones are created when the client, contractor and ops have all approved the BoQ.
                </p>
              )}
            </Card>
            <BoqCard projectId={projectId} />
            <SupervisorPicker projectId={p.id} status={p.status} />
          </div>

          <div className="flex flex-col gap-5 lg:col-span-2">
            <Card className="flex flex-col gap-3 p-4">
              <div className="flex items-center justify-between gap-3">
                <h2 className="font-semibold text-ink">Site boundary</h2>
                <Button asChild variant="outline">
                  <Link href={`/ops/projects/${p.id}/site`}>
                    <Pencil aria-hidden strokeWidth={1.75} className="size-4" />
                    {p.site ? "Change site" : "Set the site"}
                  </Link>
                </Button>
              </div>
              {p.site ? (
                <div className="h-64">
                  <GeofenceMap
                    label="Site boundary and pin"
                    pin={pin}
                    corners={corners}
                    className="h-full w-full"
                  />
                </div>
              ) : (
                <p className="type-small text-slate">The client hasn’t saved the site yet.</p>
              )}
              <p className="type-small text-slate">
                Ops can change the site at any time; the client and contractor can’t once the BoQ is approved.
                Every change is in the audit log.
              </p>
            </Card>
            <ProjectSpotChecks projectId={p.id} />
          </div>
        </div>
      </div>
    </>
  );
}
