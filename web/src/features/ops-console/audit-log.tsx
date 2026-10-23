"use client";

import { useInfiniteQuery } from "@tanstack/react-query";
import { Lock, ScrollText } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { api, call } from "@/common/api/client";
import { shortId } from "@/common/api/queries";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import type { AuditEntry } from "./queries";

// WEB-OPS-011 Audit log at /ops/audit: GET /ops/audit, newest first, filtered by action, object type, object id
// and period (the backend matches action and type exactly; actions already seen are suggested), 50 at a time.
// Choosing an entry shows what changed (before and after), with the IP and device. Not built (PACKAGE-REPORT
// W-47): the actor's name (MX-26; the id is shown, "system" when there is none), the CSV export (MX-22) and
// the agent runs tab (MX-18).

const PERIODS = [
  { value: "1", label: "Last 24 hours" },
  { value: "7", label: "Last 7 days" },
  { value: "30", label: "Last 30 days" },
  { value: "all", label: "Any time" },
] as const;

// The object types the backend records (every audit.record call in backend/app).
const OBJECT_TYPES = [
  "project",
  "site",
  "milestone",
  "verification",
  "evidence",
  "device",
  "dispute",
  "escrow_release",
  "payout",
  "payout_recipient",
  "order",
  "supplier",
  "report",
  "supervisor_profile",
  "spot_check",
  "reconciliation",
  "user",
] as const;

type Filters = { action: string; objectType: string; objectId: string; period: string };

function sinceFor(period: string): string | undefined {
  if (period === "all") return undefined;
  return new Date(Date.now() - Number(period) * 24 * 60 * 60_000).toISOString();
}

const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function useAuditSearch(filters: Filters) {
  // The start of the period is fixed when the filters change, so later pages use the same window.
  const since = useMemo(() => sinceFor(filters.period), [filters.period]);
  return useInfiniteQuery({
    queryKey: ["ops", "audit", "search", filters],
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam }) =>
      call(
        api().GET("/api/v1/ops/audit", {
          params: {
            query: {
              action: filters.action.trim() || undefined,
              object_type: filters.objectType || undefined,
              object_id: UUID.test(filters.objectId.trim()) ? filters.objectId.trim() : undefined,
              since,
              cursor: pageParam,
              limit: 50,
            },
          },
        }),
      ),
    getNextPageParam: (last) => last.next_cursor ?? undefined,
  });
}

function Json({ value, tone }: { value: unknown; tone: "before" | "after" }) {
  if (value == null)
    return <p className="type-small text-muted">Nothing (the object didn’t exist, or nothing was kept)</p>;
  return (
    <pre
      className={cn(
        "type-mono overflow-x-auto rounded-control p-3 text-ink",
        tone === "before" ? "bg-mist" : "bg-accent-tint",
      )}
    >
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}

function EntryDetail({ entry }: { entry: AuditEntry }) {
  const timeZone = useViewerTimeZone();
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="type-mono font-semibold text-ink">
          {entry.action} · {entry.object_type} {shortId(entry.object_id)}
        </h2>
        <p className="type-small text-slate">
          {entry.actor_id ? `By ${shortId(entry.actor_id)}` : "By the system"} ·{" "}
          {formatDateTime(entry.at, timeZone)}
        </p>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div className="flex flex-col gap-2">
          <p className="type-caption text-muted uppercase">Before</p>
          <Json value={entry.before} tone="before" />
        </div>
        <div className="flex flex-col gap-2">
          <p className="type-caption text-muted uppercase">After</p>
          <Json value={entry.after} tone="after" />
        </div>
      </div>
      <p className="type-small text-slate">
        Object id <span className="type-mono">{entry.object_id}</span>
        {entry.ip ? ` · IP ${entry.ip}` : ""}
        {entry.device_id ? ` · device ${entry.device_id}` : ""} · stored in UTC, shown in your time zone
      </p>
    </Card>
  );
}

export function AuditLog({ environment }: { environment: string }) {
  const timeZone = useViewerTimeZone();
  const ids = { action: useId(), type: useId(), object: useId(), period: useId(), actions: useId() };
  const [draft, setDraft] = useState<Filters>({ action: "", objectType: "", objectId: "", period: "7" });
  const [filters, setFilters] = useState<Filters>(draft);
  const [open, setOpen] = useState<string | null>(null);
  const search = useAuditSearch(filters);
  const entries = useMemo(() => search.data?.pages.flatMap((p) => p.items) ?? [], [search.data]);
  const seenActions = useMemo(() => [...new Set(entries.map((e) => e.action))].sort(), [entries]);
  const header = <OpsHeader title="Audit log" environment={environment} />;
  const badId = draft.objectId.trim() !== "" && !UUID.test(draft.objectId.trim());
  const selected = entries.find((e) => e.id === open) ?? null;

  const control = "min-h-target rounded-control border border-line-strong bg-white px-3 text-ink";
  return (
    <>
      {header}
      <div className="flex flex-col gap-4 p-5">
        <form
          className="flex flex-wrap items-end gap-3"
          onSubmit={(e) => {
            e.preventDefault();
            if (!badId) setFilters(draft);
          }}
        >
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.action} className="type-small font-semibold text-ink">
              Action
            </label>
            <input
              id={ids.action}
              list={ids.actions}
              value={draft.action}
              placeholder="e.g. milestone.claim"
              onChange={(e) => setDraft({ ...draft, action: e.target.value })}
              className={cn(control, "type-mono w-64")}
            />
            <datalist id={ids.actions}>
              {seenActions.map((a) => (
                <option key={a} value={a} />
              ))}
            </datalist>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.type} className="type-small font-semibold text-ink">
              Object
            </label>
            <select
              id={ids.type}
              value={draft.objectType}
              onChange={(e) => setDraft({ ...draft, objectType: e.target.value })}
              className={control}
            >
              <option value="">Any object</option>
              {OBJECT_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.object} className="type-small font-semibold text-ink">
              Object id
            </label>
            <input
              id={ids.object}
              value={draft.objectId}
              placeholder="Full id"
              onChange={(e) => setDraft({ ...draft, objectId: e.target.value })}
              aria-invalid={badId ? true : undefined}
              aria-describedby={badId ? `${ids.object}-problem` : undefined}
              className={cn(control, "type-mono w-80", badId && "border-bad-fg")}
            />
            {badId ? (
              <p id={`${ids.object}-problem`} className="type-small text-bad-fg">
                Paste the full id (36 characters).
              </p>
            ) : null}
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor={ids.period} className="type-small font-semibold text-ink">
              Period
            </label>
            <select
              id={ids.period}
              value={draft.period}
              onChange={(e) => setDraft({ ...draft, period: e.target.value })}
              className={control}
            >
              {PERIODS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
          <Button type="submit">Search</Button>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const reset = { action: "", objectType: "", objectId: "", period: "7" };
              setDraft(reset);
              setFilters(reset);
            }}
          >
            Clear
          </Button>
        </form>

        <p className="type-small flex items-center gap-2 text-ink">
          <Lock aria-hidden strokeWidth={1.75} className="size-4" />
          <span>
            <span className="font-semibold">Append-only and read-only.</span> No one can edit or delete an
            entry, ops included. The database refuses updates and deletes for this table.
          </span>
        </p>

        {search.isPending ? (
          <Loading label="Searching the audit log">
            <Skeleton className="h-64 w-full" />
          </Loading>
        ) : search.error ? (
          <ServerErrorContent reference={null} onRetry={() => void search.refetch()} />
        ) : entries.length ? (
          <>
            <Table caption="Audit log entries" dense>
              <thead>
                <tr>
                  <Th>Time</Th>
                  <Th>Actor</Th>
                  <Th>Action</Th>
                  <Th>Object</Th>
                  <Th>From</Th>
                </tr>
              </thead>
              <tbody>
                {entries.map((e) => (
                  <Tr key={e.id} className={cn(open === e.id && "bg-mist")}>
                    <Td>
                      <button
                        type="button"
                        aria-pressed={open === e.id}
                        onClick={() => setOpen(open === e.id ? null : e.id)}
                        className="text-left text-ink underline"
                      >
                        {formatDateTime(e.at, timeZone)}
                      </button>
                    </Td>
                    <Td className="type-mono">{e.actor_id ? shortId(e.actor_id) : "system"}</Td>
                    <Td className="type-mono">{e.action}</Td>
                    <Td>
                      {e.object_type} <span className="type-mono text-slate">{shortId(e.object_id)}</span>
                    </Td>
                    <Td className="type-mono text-slate">{e.ip ?? (e.actor_id ? "–" : "worker")}</Td>
                  </Tr>
                ))}
              </tbody>
            </Table>
            {selected ? <EntryDetail entry={selected} /> : null}
            {search.hasNextPage ? (
              <Button
                variant="secondary"
                className="self-start"
                loading={search.isFetchingNextPage}
                onClick={() => void search.fetchNextPage()}
              >
                Show 50 more
              </Button>
            ) : (
              <p className="type-small text-slate">That’s every entry for these filters.</p>
            )}
          </>
        ) : (
          <Card>
            <EmptyState icon={ScrollText} title="No entries match">
              Try a longer period or fewer filters. Actions match exactly, for example “milestone.claim”.
            </EmptyState>
          </Card>
        )}
      </div>
    </>
  );
}
