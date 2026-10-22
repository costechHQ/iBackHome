"use client";

import { useQueries } from "@tanstack/react-query";
import { House, Plus } from "lucide-react";
import Link from "next/link";

import { api, call } from "@/common/api/client";
import { keys, useProjects, type Milestone } from "@/common/api/queries";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { Button } from "@/common/ui/button";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { StatusChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";

import { projectKeys } from "./api";
import { doneCount, nextAction, setupSteps } from "./setup";

// WEB-CLIENT-003 CS-01: the client's projects, each with its set-up progress and what to do next. Names of the
// contractor and supervisor wait for MX-26, so they read "Added" / "Assigned". The budget is in naira (B-6).

function ProjectRow({ id }: { id: string }) {
  const [project, milestones, boq] = useQueries({
    queries: [
      {
        queryKey: keys.project(id),
        queryFn: () =>
          call(api().GET("/api/v1/projects/{project_id}", { params: { path: { project_id: id } } })),
      },
      {
        queryKey: keys.milestones(id),
        queryFn: () =>
          call(
            api().GET("/api/v1/projects/{project_id}/milestones", { params: { path: { project_id: id } } }),
          ),
      },
      {
        queryKey: projectKeys.boq(id),
        retry: false,
        queryFn: () =>
          call(api().GET("/api/v1/projects/{project_id}/boq", { params: { path: { project_id: id } } })),
      },
    ],
  });
  if (!project.data) return <Skeleton className="h-36 w-full" />;
  const p = project.data;
  const ms = (milestones.data ?? []) as Milestone[];
  const steps = setupSteps(p, boq.data, ms);
  const done = doneCount(steps);
  const next = nextAction(p, boq.data, ms);
  const setUp = done < steps.length;
  const href = setUp ? `/projects/${p.id}/setup` : `/projects/${p.id}`;

  return (
    <Card className="flex flex-col gap-5 p-6 lg:flex-row lg:items-center">
      <div className="flex flex-1 flex-col gap-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 className="type-h3 text-ink">
            <Link href={href} className="rounded-control hover:underline">
              {p.title}
            </Link>
          </h2>
          <StatusChip entity="project" state={p.status} audience="client" size="small" />
        </div>
        <p className="text-slate">{p.address}</p>
        <p className="type-small flex flex-wrap gap-x-6 gap-y-1 text-slate">
          <span>
            Contractor:{" "}
            <span className="font-semibold text-ink">{p.contractor_id ? "Added" : "Not yet"}</span>
          </span>
          <span>
            Supervisor:{" "}
            <span className="font-semibold text-ink">{p.supervisor_id ? "Assigned" : "Not yet"}</span>
          </span>
          <span>
            Budget:{" "}
            <span className="ibh-tabular font-semibold text-ink">
              {formatMoney(p.budget_minor, p.currency)}
            </span>
          </span>
        </p>
        {setUp ? (
          <div className="flex items-center gap-4">
            <div
              role="progressbar"
              aria-label={`Set-up ${done} of ${steps.length}`}
              aria-valuemin={0}
              aria-valuemax={steps.length}
              aria-valuenow={done}
              className="h-1.5 w-full max-w-xs overflow-hidden rounded-pill bg-line"
            >
              <div
                className="h-full bg-navy-900"
                style={{ width: `${Math.round((done / steps.length) * 100)}%` }}
              />
            </div>
            <span className="type-small whitespace-nowrap text-slate">
              Set-up {done} of {steps.length}
            </span>
          </div>
        ) : null}
      </div>
      {next ? (
        <Link href={href} className="block rounded-card bg-mist p-4 hover:bg-row-highlight lg:w-80">
          <span className="type-caption block text-muted uppercase">Next</span>
          <span className="font-semibold text-ink">{next.label}</span>
        </Link>
      ) : null}
    </Card>
  );
}

export function ProjectsList() {
  const projects = useProjects();
  if (projects.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-12">
        <Loading label="Loading your projects">
          <Skeleton className="h-9 w-48" />
          <Skeleton className="h-36 w-full" />
        </Loading>
      </div>
    );
  }
  if (!projects.data) return <ServerErrorContent reference={null} onRetry={() => void projects.refetch()} />;
  const items = projects.data.items;

  return (
    <div className="mx-auto flex w-full max-w-7xl flex-col gap-6 px-4 py-8 sm:px-12">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="type-h1 text-ink">Projects</h1>
        {items.length ? (
          <Button asChild size="lg">
            <Link href="/projects/new">
              <Plus aria-hidden strokeWidth={2} className="size-5" />
              New project
            </Link>
          </Button>
        ) : null}
      </div>
      {items.length ? (
        <ul className="flex flex-col gap-4">
          {items.map((p) => (
            <li key={p.id}>
              <ProjectRow id={p.id} />
            </li>
          ))}
        </ul>
      ) : (
        <Card>
          <EmptyState
            icon={House}
            title="No projects yet"
            action={
              <Button asChild size="lg">
                <Link href="/projects/new">Create your first project</Link>
              </Button>
            }
          >
            Start with your site address, a budget, and your contractor&apos;s phone number.
          </EmptyState>
        </Card>
      )}
    </div>
  );
}
