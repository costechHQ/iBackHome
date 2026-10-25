"use client";

import { CalendarClock, CircleCheck, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { ApiError } from "@/common/api/errors";
import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { useAssign, useSpotChecks, useSupervisors, type SupervisorRow } from "./supervision-api";
import { assignFit, splitSpotChecks } from "./supervision";

// WEB-OPS-004 "Supervisor and rotation": the vetted supervisors from GET /supervisors?project_id= (backend
// #78), each with their load and link to this project, and "Assign" (POST /projects/{id}/supervisor, which
// re-checks: 409 supervisor_not_vetted / supervisor_related_to_contractor). A relative of the contractor is
// blocked. The design's "next rotation" needs the rotation check, which has no route (PACKAGE-REPORT W-50).
// Also the project's spot checks (GET /projects/{id}/spot-checks), with a link to book one.

const REFUSALS: Record<string, string> = {
  supervisor_related_to_contractor: "They declared the contractor as a relative, so they can’t be assigned.",
  supervisor_not_vetted: "They aren’t vetted any more.",
  supervisor_suspended: "Their account is suspended.",
  project_completed: "A completed project can’t get a new supervisor.",
};

function name(s: SupervisorRow): string {
  return s.full_name ?? `Supervisor ${shortId(s.user_id)}`;
}

export function SupervisorPicker({ projectId, status }: { projectId: string; status: string }) {
  const list = useSupervisors(projectId);
  const assign = useAssign(projectId);
  const [chosen, setChosen] = useState<SupervisorRow | null>(null);
  if (list.isPending) return <Skeleton className="h-48 w-full" />;
  if (!list.data) {
    return (
      <Alert tone="bad" title="The supervisors couldn’t be loaded">
        Try again in a moment.
      </Alert>
    );
  }
  const current = list.data.find((s) => s.assigned_here) ?? null;
  const others = list.data
    .filter((s) => !s.assigned_here)
    .sort(
      (a, b) =>
        Number(Boolean(a.related_to_contractor)) - Number(Boolean(b.related_to_contractor)) ||
        a.active_projects - b.active_projects,
    );
  const refusal = assign.error instanceof ApiError ? (REFUSALS[assign.error.code] ?? null) : null;
  const done = status === "completed";

  return (
    <Card className="flex flex-col overflow-hidden">
      <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-3">
        <h2 className="font-semibold text-ink">Supervisor and rotation</h2>
        <span className="type-small flex items-center gap-1.5 text-slate">
          <RefreshCw aria-hidden strokeWidth={1.75} className="size-4" />
          Rotates after 2 milestones in a row
        </span>
      </div>
      <dl className="type-small flex justify-between gap-3 px-4 py-3">
        <dt className="text-slate">Now</dt>
        <dd className="font-semibold text-ink">
          {current ? `${name(current)} · ${current.registration_body}` : "No supervisor yet"}
        </dd>
      </dl>
      {assign.isSuccess ? (
        <div className="px-4 pb-3">
          <Alert tone="ok" title="Supervisor assigned">
            The audit log records the change. They see the project in the supervisor app.
          </Alert>
        </div>
      ) : assign.error ? (
        <div className="px-4 pb-3">
          <Alert tone="bad" title="They weren’t assigned">
            {refusal ?? "Try again."}
          </Alert>
        </div>
      ) : null}
      {done ? null : others.length ? (
        <>
          <p className="type-caption border-t border-line px-4 pt-3 text-muted uppercase">
            {current ? "Choose the next supervisor" : "Choose a supervisor"}
          </p>
          <Table caption="Vetted supervisors" dense className="rounded-none border-0">
            <thead>
              <tr>
                <Th>Supervisor</Th>
                <Th numeric>Load</Th>
                <Th>Link to this project</Th>
                <Th>
                  <span className="sr-only">Action</span>
                </Th>
              </tr>
            </thead>
            <tbody>
              {others.map((s) => {
                const fit = assignFit(s);
                return (
                  <Tr key={s.user_id}>
                    <Td>
                      <span className="block font-semibold text-ink">{name(s)}</span>
                      <span className="text-slate">{s.registration_body} · vetted</span>
                    </Td>
                    <Td numeric>
                      {s.active_projects} {s.active_projects === 1 ? "project" : "projects"}
                    </Td>
                    <Td>
                      {s.related_to_contractor ? (
                        <ToneChip label="Related to contractor" tone="bad" size="small" />
                      ) : (
                        <ToneChip label="None" tone="ok" size="small" />
                      )}
                    </Td>
                    <Td>
                      {fit.ok ? (
                        <Button
                          variant="outline"
                          onClick={() => setChosen(s)}
                          aria-label={`Assign ${name(s)}`}
                        >
                          Assign
                        </Button>
                      ) : (
                        <span className="type-small text-slate">Blocked: {fit.reason.toLowerCase()}</span>
                      )}
                    </Td>
                  </Tr>
                );
              })}
            </tbody>
          </Table>
        </>
      ) : (
        <p className="type-small border-t border-line px-4 py-3 text-slate">
          No other vetted supervisor yet. Approve applications in{" "}
          <Link href="/ops/vetting" className="font-semibold text-accent underline">
            Vetting
          </Link>
          .
        </p>
      )}
      <ConfirmDialog
        open={chosen !== null}
        onOpenChange={(open) => !open && setChosen(null)}
        title={chosen ? `Assign ${name(chosen)}?` : "Assign?"}
        description={
          current
            ? `They take over from ${name(current)}. Evidence already accepted keeps its result.`
            : "They become this project’s supervisor: they visit, capture evidence and verify milestones."
        }
        confirmLabel="Assign supervisor"
        cancelLabel="Not yet"
        busy={assign.isPending}
        onConfirm={() => chosen && assign.mutate(chosen.user_id, { onSettled: () => setChosen(null) })}
      />
    </Card>
  );
}

export function ProjectSpotChecks({ projectId }: { projectId: string }) {
  const timeZone = useViewerTimeZone();
  const checks = useSpotChecks(projectId);
  const supervisors = useSupervisors(null);
  const names = new Map((supervisors.data ?? []).map((s) => [s.user_id, name(s)]));
  if (checks.isPending) return <Skeleton className="h-24 w-full" />;
  const { upcoming, done } = splitSpotChecks(checks.data ?? []);
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold text-ink">Spot checks</h2>
        <Button asChild variant="outline">
          <Link href={`/ops/spot-checks?project=${projectId}`}>
            <CalendarClock aria-hidden strokeWidth={1.75} className="size-4" />
            Book one
          </Link>
        </Button>
      </div>
      {upcoming.length + done.length === 0 ? (
        <p className="type-small text-slate">None yet. The contractor never sees spot checks.</p>
      ) : (
        <ul className="flex flex-col gap-2">
          {[...upcoming, ...done].map((c) => (
            <li key={c.id} className="type-small flex flex-col gap-0.5 border-t border-line pt-2">
              <span className="flex items-center justify-between gap-2">
                <span className="font-semibold text-ink">
                  {formatDateTime(c.scheduled_for, timeZone)} ·{" "}
                  {names.get(c.supervisor_id) ?? shortId(c.supervisor_id)}
                </span>
                {c.completed_at ? (
                  <span className="flex items-center gap-1 text-ok-fg">
                    <CircleCheck aria-hidden strokeWidth={1.75} className="size-4" /> Done
                  </span>
                ) : (
                  <ToneChip label="Scheduled" tone="neutral" size="small" />
                )}
              </span>
              {c.findings ? <span className="text-slate">“{c.findings}”</span> : null}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
