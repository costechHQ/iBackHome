"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Flag } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { shortId, useEvidence, useProjects } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ThreeChecksList } from "@/common/ui/evidence";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, EmptyState } from "@/common/ui/surfaces";

import { waited } from "./ops";
import { keys, useOpsQueue } from "./queries";

// WEB-OPS-005 Flagged evidence at /ops/evidence and /ops/evidence/:id: the queue from GET /ops/queue, and one
// capture with the reason it was flagged, where and when it was taken, and the decision (accept, or reject
// with notes; POST /evidence/{id}/decision). The capture is read from the project's gallery (there's no
// single-evidence read, MX-07), so the design's matched earlier photo, the match distance and the hashes side
// by side aren't shown (PACKAGE-REPORT W-44); the reason says what the server found. Names wait for MX-26.

type QueueItem = {
  evidence_id: string;
  project_id: string;
  kind: string;
  captured_at: string;
  reason: string | null;
  flagged_at: string;
};

const ROLE: Record<string, string> = { supervisor: "Supervisor", contractor: "Contractor" };

function QueueList({
  items,
  current,
  titles,
}: {
  items: readonly QueueItem[];
  current: string | null;
  titles: ReadonlyMap<string, string>;
}) {
  return (
    <Card className="flex flex-col overflow-hidden">
      <h2 className="border-b border-line px-4 py-3 font-semibold text-ink">Queue · {items.length}</h2>
      {items.length ? (
        <ul>
          {items.map((e) => (
            <li key={e.evidence_id} className="border-b border-line last:border-b-0">
              <Link
                href={`/ops/evidence/${e.evidence_id}`}
                aria-current={e.evidence_id === current ? "page" : undefined}
                className={cn(
                  "flex flex-col gap-1 px-4 py-3 hover:bg-mist",
                  e.evidence_id === current && "border-l-4 border-navy-900 bg-mist",
                )}
              >
                <span className="type-mono font-semibold text-ink">EV-{shortId(e.evidence_id)}</span>
                <span className="type-small text-slate">
                  {titles.get(e.project_id) ?? "Project"} · {e.kind} · flagged {waited(e.flagged_at)} ago
                </span>
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <EmptyState icon={CircleCheck} title="Nothing flagged" />
      )}
      <p className="type-small border-t border-line px-4 py-3 text-slate">
        Flagged means a check needs a person: usually the image looks like an earlier one. The client sees it
        as under review until you decide.
      </p>
    </Card>
  );
}

function useDecide(evidenceId: string, projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (body: { decision: "accepted" | "rejected"; notes: string }, key: string) =>
      call(
        api().POST("/api/v1/evidence/{evidence_id}/decision", {
          params: { path: { evidence_id: evidenceId } },
          body,
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: keys.queue() });
        void queries.invalidateQueries({ queryKey: ["project", projectId, "evidence"] });
      },
    },
  );
}

function Decision({ item, next }: { item: QueueItem; next: string | null }) {
  const router = useRouter();
  const notesId = useId();
  const [notes, setNotes] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const decide = useDecide(item.evidence_id, item.project_id);
  const done = decide.data?.status;
  const send = (decision: "accepted" | "rejected") => {
    if (decision === "rejected" && !notes.trim()) {
      setProblem("Say why it’s rejected: the supervisor sees this.");
      return;
    }
    setProblem(null);
    decide.mutate({ decision, notes: notes.trim() });
  };
  if (done) {
    return (
      <Card className="flex flex-col gap-3 p-4">
        <Alert
          tone={done === "accepted" ? "ok" : "neutral"}
          title={done === "accepted" ? "Accepted" : "Rejected"}
        >
          {done === "accepted"
            ? "It now counts as evidence and the client sees it with its checks passed."
            : "It won’t count. The supervisor sees your notes and can capture again."}
        </Alert>
        {next ? (
          <Button onClick={() => router.push(`/ops/evidence/${next}`)}>Next in the queue</Button>
        ) : (
          <Button asChild variant="secondary">
            <Link href="/ops/evidence">Back to the queue</Link>
          </Button>
        )}
      </Card>
    );
  }
  const conflict = decide.error instanceof ApiError && decide.error.status === 409;
  return (
    <Card className="flex flex-col gap-3 p-4">
      <h2 className="font-semibold text-ink">Decision</h2>
      {conflict ? (
        <Alert tone="warn" title="Someone already decided this">
          Another ops person accepted or rejected it. Refresh the queue.
        </Alert>
      ) : decide.error ? (
        <Alert tone="bad" title="The decision wasn’t saved">
          Try again.
        </Alert>
      ) : null}
      <div className="flex flex-col gap-1.5">
        <label htmlFor={notesId} className="type-small font-semibold text-ink">
          Notes <span className="font-normal text-slate">(required to reject)</span>
        </label>
        <textarea
          id={notesId}
          rows={4}
          maxLength={1000}
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? `${notesId}-problem` : undefined}
          className={cn(
            "rounded-control border bg-white px-3 py-2 text-ink",
            problem ? "border-bad-fg" : "border-line-strong",
          )}
        />
        {problem ? (
          <p id={`${notesId}-problem`} className="type-small text-bad-fg">
            {problem}
          </p>
        ) : null}
      </div>
      <div className="flex flex-wrap gap-3">
        <Button
          loading={decide.isPending && decide.variables?.decision === "accepted"}
          onClick={() => send("accepted")}
        >
          Accept
        </Button>
        <Button
          variant="destructive"
          loading={decide.isPending && decide.variables?.decision === "rejected"}
          onClick={() => send("rejected")}
        >
          Reject
        </Button>
      </div>
      <p className="type-small text-slate">
        The supervisor and client see the result. Notes go in the audit log.
      </p>
    </Card>
  );
}

function Capture({ item }: { item: QueueItem }) {
  const timeZone = useViewerTimeZone();
  const gallery = useEvidence(item.project_id, { status: "flagged" });
  const e = gallery.data?.find((x) => x.id === item.evidence_id);
  if (gallery.isPending) return <Skeleton className="h-96 w-full" />;
  if (!e) {
    return (
      <Alert tone="warn" title="This capture couldn’t be loaded">
        It may have been decided already. Go back to the queue.
      </Alert>
    );
  }
  const rows: [string, string][] = [
    ["Captured", formatDateTime(e.captured_at, timeZone)],
    ["GPS time", formatDateTime(e.gps_time, timeZone)],
    ["Uploaded", formatDateTime(e.created_at, timeZone)],
    ["By", `${ROLE[e.captured_by_role] ?? e.captured_by_role} · ${shortId(e.captured_by)}`],
    ["Place", `${e.latitude.toFixed(6)}, ${e.longitude.toFixed(6)} · ±${Math.round(e.accuracy_m)} m`],
    ["Device", e.device_id],
    ["File hash", e.file_sha256.slice(0, 16)],
  ];
  return (
    <div className="flex flex-col gap-4">
      <Card className="overflow-hidden">
        <div className="flex items-center justify-between gap-3 border-b border-line px-4 py-2">
          <ToneChip label={`Flagged · EV-${shortId(e.id)}`} tone="warn" size="small" />
          {e.milestone_id ? <span className="type-small text-slate">For a milestone claim</span> : null}
        </div>
        <div className="flex h-96 items-center justify-center bg-placeholder">
          {e.kind === "video" ? (
            <video src={e.read_url} controls className="max-h-full max-w-full">
              <track kind="captions" />
            </video>
          ) : (
            // eslint-disable-next-line @next/next/no-img-element -- a 15-minute signed URL; next/image would proxy it
            <img
              src={e.read_url}
              alt={`Flagged capture EV-${shortId(e.id)}`}
              className="max-h-full max-w-full object-contain"
            />
          )}
        </div>
      </Card>
      {item.reason ? (
        <Alert tone="warn" title="Why it was flagged">
          {item.reason}
        </Alert>
      ) : null}
      <Card className="p-4">
        <ThreeChecksList status={e.status} rejectReason={e.reject_reason} />
        <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
          {rows.map(([k, v]) => (
            <div key={k} className="flex flex-col">
              <dt className="type-small text-slate">{k}</dt>
              <dd className="type-small text-ink">{v}</dd>
            </div>
          ))}
        </dl>
      </Card>
    </div>
  );
}

export function FlaggedEvidence({
  evidenceId,
  environment,
}: {
  evidenceId: string | null;
  environment: string;
}) {
  const queue = useOpsQueue();
  const projects = useProjects();
  const title = evidenceId ? `Flagged evidence · EV-${shortId(evidenceId)}` : "Flagged evidence";
  const header = <OpsHeader title={title} environment={environment} />;
  const items = [...(queue.data?.flagged_evidence ?? [])].sort((a, b) =>
    a.flagged_at.localeCompare(b.flagged_at),
  );
  // Keep showing the one just decided (it leaves the queue) until ops moves on.
  const kept = useKeep(items.find((i) => i.evidence_id === evidenceId) ?? null);
  if (queue.isPending || projects.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading flagged evidence">
            <Skeleton className="h-96 w-full" />
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
  const titles = new Map((projects.data?.items ?? []).map((p) => [p.id, p.title]));
  const item =
    items.find((i) => i.evidence_id === evidenceId) ?? (kept?.evidence_id === evidenceId ? kept : null);
  const next = items.find((i) => i.evidence_id !== evidenceId)?.evidence_id ?? null;

  return (
    <>
      {header}
      <div className="grid gap-5 p-5 lg:grid-cols-4">
        <QueueList items={items} current={evidenceId} titles={titles} />
        <div className="flex flex-col gap-4 lg:col-span-3">
          {!evidenceId ? (
            items.length ? (
              <Card>
                <EmptyState icon={Flag} title="Choose a capture from the queue">
                  Oldest first. Each one stays under review for the client until you decide.
                </EmptyState>
              </Card>
            ) : null
          ) : !item ? (
            <Alert tone="info" title="This capture isn’t in the queue">
              It has been decided already, or it was never flagged.{" "}
              <Link href="/ops/evidence" className="font-semibold text-accent underline">
                Back to the queue
              </Link>
            </Alert>
          ) : (
            <>
              <p className="type-small text-slate">
                <span className="font-semibold text-ink">{titles.get(item.project_id) ?? "Project"}</span> ·{" "}
                {item.kind} · flagged {waited(item.flagged_at)} ago
              </p>
              <div className="grid gap-4 lg:grid-cols-3">
                <div className="lg:col-span-2">
                  <Capture item={item} />
                </div>
                <Decision key={item.evidence_id} item={item} next={next} />
              </div>
            </>
          )}
        </div>
      </div>
    </>
  );
}

/** Remembers the last non-null value, so a decided capture stays on screen after it leaves the queue. */
function useKeep<T>(value: T | null): T | null {
  const [kept, setKept] = useState<T | null>(value);
  if (value !== null && value !== kept) setKept(value);
  return value ?? kept;
}
