"use client";

import { useQueries } from "@tanstack/react-query";
import Link from "next/link";

import { api, call } from "@/common/api/client";
import { keys, ledgerQuery, type Milestone } from "@/common/api/queries";
import { formatMoney } from "@/common/money";
import { Skeleton } from "@/common/ui/skeleton";
import { StatusChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";
import { moneySummary } from "@/features/dashboard/money-summary";

import { projectKeys } from "./api";
import { doneCount, nextAction, setupSteps } from "./setup";

// One project card (WEB-CLIENT-003 CS-01, and "Your projects" on the client home, WEB-CLIENT-008): set-up
// progress and the next step while it is being set up, then milestones released and the money released and
// held (client currency where the ledger allows). Names of the contractor and supervisor wait for MX-26, so
// they read "Added" / "Assigned". The budget is in naira (B-6).

export function ProjectRow({ id }: { id: string }) {
  const [project, milestones, boq, ledger] = useQueries({
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
      ledgerQuery(id),
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
  const money = !setUp && ledger.data ? moneySummary(ms, ledger.data.ledger) : null;
  const released = ms.filter((m) => m.status === "released").length;
  const current = [...ms].sort((a, b) => a.sequence - b.sequence).find((m) => m.status !== "released");

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
        ) : (
          <div className="flex flex-col gap-1">
            <p className="text-ink">
              {released} of {ms.length} milestones released
              {current
                ? ` · ${current.name}: ${current.status === "verified" ? "waiting for you" : current.status}`
                : ""}
            </p>
            {money ? (
              <p className="type-small ibh-tabular flex flex-wrap gap-x-6 text-slate">
                <span>
                  Released{" "}
                  <span className="font-semibold text-ink">
                    {money.releasedClient
                      ? formatMoney(money.releasedClient.amountMinor, money.releasedClient.currency)
                      : formatMoney(money.releasedNgn, "NGN")}
                  </span>
                </span>
                <span>
                  In escrow{" "}
                  <span className="font-semibold text-ink">
                    {money.escrow.client
                      ? formatMoney(money.escrow.client.amountMinor, money.escrow.client.currency)
                      : formatMoney(money.escrow.ngnMinor, "NGN")}
                  </span>
                </span>
              </p>
            ) : null}
          </div>
        )}
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
