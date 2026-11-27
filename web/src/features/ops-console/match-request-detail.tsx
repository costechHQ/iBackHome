"use client";

import Link from "next/link";
import { useId, useState, type ReactNode } from "react";

import { ApiError } from "@/common/api/errors";
import { useMatchRequest, useProject, type MatchRequest } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { SelectField } from "@/common/ui/field";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

import { listText, SPECIALTY_LABELS, specialtyLabel } from "./contractors";
import { useContractorDirectory, type Contractor } from "./contractors-api";
import {
  canSend,
  isActive,
  MATCH_STATUS,
  move,
  SHORTLIST_MAX,
  toggleChoice,
  type MatchStatus,
} from "./matching";
import { useCancelRequest, useSetShortlist } from "./matching-api";

// One match request at /ops/match-requests/:projectId (ADR 0007, phase 2): the client's brief and the
// shortlist builder. The directory starts filtered to the request's state and kind of work (clear either to
// widen it); tick up to three contractors, set the order the client will see them in, and send. Only approved,
// listed contractors with an active account are offered, and the backend refuses any other (422). Phone each
// contractor before you send: the client is told as soon as you do.

function Facts({ rows }: { rows: readonly (readonly [string, ReactNode])[] }) {
  return (
    <dl className="type-small flex flex-col gap-1.5">
      {rows.map(([k, v]) => (
        <div key={k} className="flex justify-between gap-3">
          <dt className="text-slate">{k}</dt>
          <dd className="text-right font-semibold text-ink">{v}</dd>
        </div>
      ))}
    </dl>
  );
}

function errorText(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.code === "contractor_not_available") {
      return "One of those contractors is no longer approved, listed and active. Reload and pick again.";
    }
    if (error.code === "invalid_transition") return "This request was decided meanwhile. Reload the page.";
    if (error.code === "project_not_draft" || error.code === "project_has_contractor") {
      return "The project has moved on, so a shortlist can't be set any more.";
    }
  }
  return "Try again.";
}

function Builder({ request, projectId }: { request: MatchRequest; projectId: string }) {
  const noteId = useId();
  const current = request.shortlist.map((c) => c.id);
  const [selected, setSelected] = useState<string[]>(current);
  const [state, setState] = useState(request.state);
  const [kind, setKind] = useState(request.work_type);
  const [note, setNote] = useState("");
  const [confirm, setConfirm] = useState(false);
  const directory = useContractorDirectory(state, kind, true);
  const send = useSetShortlist(request.id, projectId);
  const replacing = request.status === "shortlisted";

  // The directory page may not hold a contractor already shortlisted under another filter: keep their card.
  const known = new Map<string, Contractor | MatchRequest["shortlist"][number]>();
  for (const c of request.shortlist) known.set(c.id, c);
  for (const c of directory.data?.items ?? []) known.set(c.id, c);
  const name = (id: string) => known.get(id)?.business_name ?? "A contractor";

  return (
    <div className="grid gap-5 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        <Card className="flex flex-col gap-3 p-4">
          <h2 className="font-semibold text-ink">Contractors to choose from</h2>
          <div className="flex flex-wrap gap-3">
            <SelectField
              label="State"
              value={state}
              onChange={(e) => setState(e.target.value)}
              className="w-48"
            >
              <option value="">Any state</option>
              {NIGERIAN_STATES.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </SelectField>
            <SelectField
              label="Kind of work"
              value={kind}
              onChange={(e) => setKind(e.target.value as typeof kind)}
              className="w-48"
            >
              <option value="">Any kind</option>
              {Object.entries(SPECIALTY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </SelectField>
          </div>
          {directory.isPending ? (
            <Loading label="Loading contractors">
              <Skeleton className="h-32 w-full" />
            </Loading>
          ) : !directory.data ? (
            <ServerErrorContent reference={null} onRetry={() => void directory.refetch()} />
          ) : directory.data.items.length ? (
            <ul className="flex flex-col gap-2">
              {directory.data.items.map((c) => {
                const on = selected.includes(c.id);
                const full = !on && selected.length >= SHORTLIST_MAX;
                return (
                  <li key={c.id} className="rounded-control border border-line p-3">
                    <label className="flex items-start gap-3 text-ink">
                      <input
                        type="checkbox"
                        checked={on}
                        disabled={full}
                        onChange={() => setSelected(toggleChoice(selected, c.id))}
                        aria-label={`Put ${c.business_name} forward`}
                        className="mt-1 size-5 flex-none"
                      />
                      <span className="flex flex-col gap-1">
                        <span className="font-semibold">{c.business_name}</span>
                        <span className="type-small text-slate">{c.summary}</span>
                        <span className="type-small text-muted">
                          {listText(c.states_served)} · {listText(c.specialties, specialtyLabel)} ·{" "}
                          {c.years_in_business} yrs · {c.projects_completed} projects
                        </span>
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
          ) : (
            <p className="type-small text-slate">
              No approved, listed contractor matches. Widen the state or the kind of work.
            </p>
          )}
        </Card>
      </div>

      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-4">
          <h2 className="font-semibold text-ink">
            The shortlist{" "}
            <span className="type-small font-normal text-slate">
              ({selected.length} of {SHORTLIST_MAX})
            </span>
          </h2>
          {selected.length ? (
            <ol className="flex flex-col gap-2">
              {selected.map((id, i) => (
                <li
                  key={id}
                  className="flex items-center justify-between gap-2 rounded-control bg-mist px-3 py-2"
                >
                  <span className="type-small font-semibold text-ink">
                    {i + 1}. {name(id)}
                  </span>
                  <span className="flex gap-1">
                    <Button
                      variant="secondary"
                      aria-label={`Move ${name(id)} up`}
                      disabled={i === 0}
                      onClick={() => setSelected(move(selected, id, -1))}
                    >
                      ↑
                    </Button>
                    <Button
                      variant="secondary"
                      aria-label={`Move ${name(id)} down`}
                      disabled={i === selected.length - 1}
                      onClick={() => setSelected(move(selected, id, 1))}
                    >
                      ↓
                    </Button>
                  </span>
                </li>
              ))}
            </ol>
          ) : (
            <p className="type-small text-slate">Tick one to three contractors on the left.</p>
          )}
          <div className="flex flex-col gap-1.5">
            <label htmlFor={noteId} className="type-small font-semibold text-ink">
              Your note{" "}
              <span className="font-normal text-slate">(for ops only; the client never sees it)</span>
            </label>
            <textarea
              id={noteId}
              rows={3}
              maxLength={1000}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              className="rounded-control border border-line-strong bg-white px-3 py-2 text-ink"
            />
          </div>
          {send.isError ? (
            <Alert tone="bad" title="The shortlist wasn’t saved">
              {errorText(send.error)}
            </Alert>
          ) : null}
          <Button
            size="lg"
            disabled={!canSend(selected)}
            loading={send.isPending}
            onClick={() => setConfirm(true)}
          >
            {replacing ? "Replace the shortlist" : "Send the shortlist to the client"}
          </Button>
          <p className="type-small text-slate">
            The client is told straight away. Phone each contractor first to check they are free and
            interested.
          </p>
        </Card>
      </div>

      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title={replacing ? "Replace the shortlist?" : "Send this shortlist?"}
        description={
          <>
            The client will see{" "}
            {selected.length === 1 ? "this contractor" : `these ${selected.length} contractors`}:{" "}
            {selected.map(name).join(", ")}. They are told now and choose one. Have you phoned each of them?
          </>
        }
        confirmLabel="Yes, send it"
        cancelLabel="Not yet"
        busy={send.isPending}
        onConfirm={() =>
          send.mutate(
            { contractorIds: selected, note: note.trim() || null },
            { onSettled: () => setConfirm(false) },
          )
        }
      />
    </div>
  );
}

function Detail({ request, projectId, title }: { request: MatchRequest; projectId: string; title: string }) {
  const timeZone = useViewerTimeZone();
  const reasonId = useId();
  const [reason, setReason] = useState("");
  const [confirm, setConfirm] = useState(false);
  const cancel = useCancelRequest(request.id, projectId);
  const status = MATCH_STATUS[request.status as MatchStatus] ?? {
    label: request.status,
    tone: "neutral" as const,
  };
  const active = isActive(request.status);
  return (
    <div className="flex flex-col gap-5 p-5">
      <div className="grid gap-5 lg:grid-cols-3">
        <Card className="flex flex-col gap-3 p-4 lg:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold text-ink">The brief</h2>
            <ToneChip label={status.label} tone={status.tone} size="small" />
          </div>
          <Facts
            rows={[
              [
                "Project",
                <Link key="p" href={`/ops/projects/${projectId}`} className="underline">
                  {title}
                </Link>,
              ],
              ["Where", `${request.city}, ${request.state}`],
              ["Kind of work", specialtyLabel(request.work_type)],
              ["When", request.timeline],
              ["Budget", formatMoney(request.budget_minor, request.currency)],
              ["Asked", formatDateTime(request.created_at, timeZone)],
              ...(request.notes ? ([["Notes", request.notes]] as const) : []),
            ]}
          />
        </Card>
        <Card className="flex flex-col gap-3 p-4">
          <h2 className="font-semibold text-ink">Cancel</h2>
          {!active ? (
            <p className="type-small text-slate">
              {request.status === "matched"
                ? `The client chose ${request.chosen?.business_name ?? "a contractor"}.`
                : `Cancelled${request.decided_at ? ` ${formatDateTime(request.decided_at, timeZone)}` : ""}.${request.cancel_reason ? ` Reason: ${request.cancel_reason}` : ""}`}
            </p>
          ) : (
            <>
              <label htmlFor={reasonId} className="type-small text-slate">
                Reason (optional)
              </label>
              <textarea
                id={reasonId}
                rows={2}
                maxLength={500}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                className="rounded-control border border-line-strong bg-white px-3 py-2 text-ink"
              />
              {cancel.isError ? (
                <Alert tone="bad" title="Not cancelled">
                  {errorText(cancel.error)}
                </Alert>
              ) : null}
              <Button variant="destructive" className="self-start" onClick={() => setConfirm(true)}>
                Cancel the request
              </Button>
            </>
          )}
        </Card>
      </div>
      {request.status === "shortlisted" || request.status === "matched" ? (
        <Card className="flex flex-col gap-2 p-4">
          <h2 className="font-semibold text-ink">
            {request.status === "matched" ? "What the client chose from" : "What the client sees"}
          </h2>
          <ol className="type-small flex flex-col gap-1 text-slate">
            {request.shortlist.map((c, i) => (
              <li key={c.id}>
                {i + 1}. <span className="font-semibold text-ink">{c.business_name}</span> ·{" "}
                {c.states_served.join(", ")} · {c.years_in_business} yrs
                {request.chosen?.id === c.id ? " · chosen" : ""}
              </li>
            ))}
          </ol>
        </Card>
      ) : null}
      {active ? (
        <Builder
          key={`${request.id}-${request.shortlist.map((c) => c.id).join()}`}
          request={request}
          projectId={projectId}
        />
      ) : null}
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Cancel this request?"
        description="The client is not told automatically. They can send a new request any time while the project is a draft."
        confirmLabel="Cancel the request"
        cancelLabel="Keep it"
        destructive
        busy={cancel.isPending}
        onConfirm={() => cancel.mutate(reason.trim() || null, { onSettled: () => setConfirm(false) })}
      />
    </div>
  );
}

export function MatchRequestDetail({ projectId, environment }: { projectId: string; environment: string }) {
  const request = useMatchRequest(projectId);
  const project = useProject(projectId);
  const title = project.data?.title ?? "Project";
  const header = <OpsHeader title={`${title} · contractor request`} environment={environment} />;
  if (request.isPending || project.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the request">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (request.isError || !project.data) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void request.refetch()} />
      </>
    );
  }
  if (!request.data) return <NotFoundContent />;
  return (
    <>
      {header}
      <div className="px-5 pt-4">
        <Link href="/ops/match-requests" className="type-small font-semibold text-accent">
          ‹ Match requests
        </Link>
      </div>
      <Detail request={request.data} projectId={projectId} title={title} />
    </>
  );
}
