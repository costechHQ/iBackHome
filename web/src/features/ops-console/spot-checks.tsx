"use client";

import { useQueries } from "@tanstack/react-query";
import { CalendarClock, Lock } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { ApiError } from "@/common/api/errors";
import { shortId, useProjects } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { spotChecksQuery, useScheduleSpotCheck, useSupervisors, type SpotCheck } from "./supervision-api";
import { splitSpotChecks, spotCheckFit, watDateTime } from "./supervision";

// WEB-OPS-007 Spot checks at /ops/spot-checks: book an unannounced visit (POST /projects/{id}/spot-checks) by a
// vetted supervisor who isn't the project's own and isn't related to its contractor (GET /supervisors with
// project_id, backend #78), on a day and time in WAT; then every project's upcoming visits and results
// (GET /projects/{id}/spot-checks, read project by project). The contractor never sees any of it. Not built
// (PACKAGE-REPORT W-51): "Window", "What to check", "Matches claim", "Visible to client", "Close and share with
// client" and "Link to dispute" (no fields or routes, MX-14).

const LIVE = new Set(["active", "paused"]);
const control = "min-h-12 w-full rounded-control border bg-white px-3.5 text-ink";

function BookForm({
  projects,
  initial,
}: {
  projects: { id: string; title: string }[];
  initial: string | null;
}) {
  const ids = { project: useId(), supervisor: useId(), day: useId(), time: useId() };
  const [projectId, setProjectId] = useState(
    initial && projects.some((p) => p.id === initial) ? initial : "",
  );
  const [supervisorId, setSupervisorId] = useState("");
  const [day, setDay] = useState("");
  const [time, setTime] = useState("10:00");
  const [problem, setProblem] = useState<string | null>(null);
  const candidates = useSupervisors(projectId || null);
  const schedule = useScheduleSpotCheck();
  const rows = projectId ? (candidates.data ?? []) : [];
  const chosen = rows.find((s) => s.user_id === supervisorId);
  const failure = schedule.error instanceof ApiError ? schedule.error.code : schedule.error ? "error" : null;

  return (
    <Card className="flex flex-col gap-4 p-4">
      <h2 className="font-semibold text-ink">Schedule a spot check</h2>
      {schedule.isSuccess ? (
        <Alert tone="ok" title="Spot check booked">
          It’s on the supervisor’s list in their app. The contractor isn’t told.
        </Alert>
      ) : failure ? (
        <Alert tone="bad" title="It wasn’t booked">
          {failure === "spot_check_in_past"
            ? "Choose a time in the future."
            : failure === "supervisor_related_to_contractor"
              ? "That supervisor declared the contractor as a relative."
              : failure === "spot_check_by_assigned_supervisor"
                ? "Choose someone other than the project’s own supervisor."
                : "Try again."}
        </Alert>
      ) : null}
      <form
        noValidate
        className="flex flex-col gap-4"
        onSubmit={(e) => {
          e.preventDefault();
          const when = watDateTime(day, time);
          if (!projectId || !supervisorId) return setProblem("Choose a project and a supervisor.");
          if (!when) return setProblem("Choose a day and a time.");
          if (Date.parse(when) <= Date.now()) return setProblem("Choose a time in the future.");
          setProblem(null);
          schedule.mutate({ projectId, supervisorId, scheduledFor: when });
        }}
      >
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.project} className="type-small font-semibold text-ink">
            Project
          </label>
          <select
            id={ids.project}
            value={projectId}
            onChange={(e) => {
              setProjectId(e.target.value);
              setSupervisorId("");
              schedule.reset();
            }}
            className={`${control} border-line-strong`}
          >
            <option value="">Choose a live project</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.title}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.supervisor} className="type-small font-semibold text-ink">
            Supervisor
          </label>
          <select
            id={ids.supervisor}
            value={supervisorId}
            disabled={!projectId || candidates.isPending}
            onChange={(e) => setSupervisorId(e.target.value)}
            aria-describedby={`${ids.supervisor}-help`}
            className={`${control} border-line-strong disabled:bg-mist`}
          >
            <option value="">{projectId ? "Choose a supervisor" : "Choose the project first"}</option>
            {rows.map((s) => {
              const fit = spotCheckFit(s);
              return (
                <option key={s.user_id} value={s.user_id} disabled={!fit.ok}>
                  {s.full_name ?? `Supervisor ${shortId(s.user_id)}`}
                  {fit.ok
                    ? ` · ${s.active_projects} projects`
                    : ` · not eligible: ${fit.reason.toLowerCase()}`}
                </option>
              );
            })}
          </select>
          <p id={`${ids.supervisor}-help`} className="type-small text-slate">
            {chosen
              ? "Not assigned to this project · no declared link to its contractor"
              : "The project’s own supervisor and relatives of its contractor can’t be chosen."}
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.day} className="type-small font-semibold text-ink">
              Day
            </label>
            <input
              id={ids.day}
              type="date"
              value={day}
              onChange={(e) => setDay(e.target.value)}
              className={`${control} border-line-strong`}
            />
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.time} className="type-small font-semibold text-ink">
              Time (WAT)
            </label>
            <input
              id={ids.time}
              type="time"
              value={time}
              onChange={(e) => setTime(e.target.value)}
              className={`${control} border-line-strong`}
            />
          </div>
        </div>
        {problem ? (
          <p role="alert" className="type-small text-bad-fg">
            {problem}
          </p>
        ) : null}
        <p className="type-small flex items-start gap-2 rounded-control bg-mist p-3 text-ink">
          <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
          Unannounced. The contractor never sees it.
        </p>
        <Button type="submit" size="lg" loading={schedule.isPending}>
          Schedule spot check
        </Button>
      </form>
    </Card>
  );
}

export function SpotChecks({
  environment,
  initialProject,
}: {
  environment: string;
  initialProject: string | null;
}) {
  const timeZone = useViewerTimeZone();
  const projects = useProjects();
  const supervisors = useSupervisors(null);
  const items = projects.data?.items ?? [];
  const lists = useQueries({ queries: items.map((p) => spotChecksQuery(p.id)) });
  const header = <OpsHeader title="Spot checks" environment={environment} />;

  if (projects.isPending || lists.some((q) => q.isPending)) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the spot checks">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (projects.error) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void projects.refetch()} />
      </>
    );
  }

  const titles = new Map(items.map((p) => [p.id, p.title]));
  const names = new Map(
    (supervisors.data ?? []).map((s) => [s.user_id, s.full_name ?? `Supervisor ${shortId(s.user_id)}`]),
  );
  const all = lists.flatMap((q) => (q.data ?? []) as SpotCheck[]);
  const { upcoming, done } = splitSpotChecks(all);
  const live = items.filter((p) => LIVE.has(p.status)).map((p) => ({ id: p.id, title: p.title }));
  const who = (id: string) => names.get(id) ?? shortId(id);

  return (
    <>
      {header}
      <div className="grid gap-5 p-5 lg:grid-cols-5">
        <div className="flex flex-col gap-5 lg:col-span-2">
          <BookForm projects={live} initial={initialProject} />
          <Card className="overflow-hidden">
            <h2 className="border-b border-line px-4 py-3 font-semibold text-ink">
              Upcoming · {upcoming.length}
            </h2>
            {upcoming.length ? (
              <ul>
                {upcoming.map((c) => (
                  <li
                    key={c.id}
                    className="flex items-center justify-between gap-3 border-b border-line px-4 py-3 last:border-b-0"
                  >
                    <span className="flex flex-col">
                      <Link
                        href={`/ops/projects/${c.project_id}`}
                        className="font-semibold text-ink underline"
                      >
                        {titles.get(c.project_id) ?? "Project"}
                      </Link>
                      <span className="type-small text-slate">
                        {formatDateTime(c.scheduled_for, timeZone)} · {who(c.supervisor_id)}
                      </span>
                    </span>
                    <ToneChip label="Scheduled" tone="neutral" size="small" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="type-small px-4 py-3 text-slate">Nothing booked.</p>
            )}
          </Card>
        </div>
        <Card className="overflow-hidden lg:col-span-3">
          <h2 className="border-b border-line px-4 py-3 font-semibold text-ink">Results</h2>
          {done.length ? (
            <Table caption="Spot-check results" dense className="rounded-none border-0">
              <thead>
                <tr>
                  <Th>Project</Th>
                  <Th>Supervisor</Th>
                  <Th>Done</Th>
                  <Th>Findings</Th>
                </tr>
              </thead>
              <tbody>
                {done.map((c) => (
                  <Tr key={c.id}>
                    <Td className="font-semibold text-ink">{titles.get(c.project_id) ?? "Project"}</Td>
                    <Td>{who(c.supervisor_id)}</Td>
                    <Td>{c.completed_at ? formatDateTime(c.completed_at, timeZone) : "–"}</Td>
                    <Td className="text-slate">{c.findings}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
          ) : (
            <EmptyState icon={CalendarClock} title="No results yet">
              When the visiting supervisor records what they found, it shows here.
            </EmptyState>
          )}
        </Card>
      </div>
    </>
  );
}
