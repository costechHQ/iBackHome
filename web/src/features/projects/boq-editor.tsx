"use client";

import { useQueryClient } from "@tanstack/react-query";
import { CircleCheck, Lock, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError, toUiState } from "@/common/api/errors";
import { keys } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";
import { useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ConfirmDialog } from "@/common/ui/dialog";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";
import { Table, Td, Th, Tr } from "@/common/ui/table";

import { projectKeys, useApproveBoq, useBoq, usePriceIndex, type Boq } from "./api";
import {
  COMMON_UNITS,
  draftFrom,
  draftTotal,
  emptyLine,
  emptyMilestone,
  fieldId,
  FLAG_PERCENT,
  indexHint,
  isBlank,
  issues as findIssues,
  LIMITS,
  lineCount,
  lineTotal,
  milestoneTotal,
  quantityText,
  toSubmit,
  type Draft,
  type DraftLine,
  type DraftMilestone,
  type IndexEntry,
  type Issue,
} from "./boq-draft";

// WEB-CONTRACTOR-004 BoQ editor at /c/projects/:id/boq. The contractor prices the work in naira, line by line,
// grouped into milestones; totals here are a preview and the server works out the saved ones. Submitting saves
// the BoQ (PUT, which moves a draft project to BoQ review) and records the contractor's approval, as the design
// says. In review the BoQ can be revised, which clears every approval (the backend does that); once the project
// is active it's locked. Not built (PACKAGE-REPORT W-38): the "agreed contract sum" (the backend has the client's
// budget instead), "Client sees ≈ $" (no rate before funding, B-6), versions and "Compare with version 1",
// "Sent back" (MX-08), and saving a draft on the server: unsent changes are kept in this browser until submitted.

const SETTING_UP = new Set(["draft", "boq_review"]);

const ROLE_NAMES: Record<string, string> = { contractor: "You", client: "Your client", ops: "iBackHome ops" };

const storageKey = (projectId: string) => `ibh-boq-draft:${projectId}`;

function readStored(projectId: string): Draft | null {
  try {
    const raw = window.localStorage.getItem(storageKey(projectId));
    const parsed = raw ? (JSON.parse(raw) as Draft) : null;
    return parsed && Array.isArray(parsed.milestones) && parsed.milestones.length ? parsed : null;
  } catch {
    return null;
  }
}

function writeStored(projectId: string, draft: Draft | null) {
  try {
    if (draft) window.localStorage.setItem(storageKey(projectId), JSON.stringify(draft));
    else window.localStorage.removeItem(storageKey(projectId));
  } catch {
    // Private windows and blocked storage: the draft just isn't kept.
  }
}

function useSubmitBoq(projectId: string) {
  const queries = useQueryClient();
  return useWrite(
    (body: ReturnType<typeof toSubmit>, key: string) =>
      call(
        api().PUT("/api/v1/projects/{project_id}/boq", {
          params: { path: { project_id: projectId } },
          body,
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSuccess: (boq) => queries.setQueryData(projectKeys.boq(projectId), boq),
      onSettled: () => {
        void queries.invalidateQueries({ queryKey: keys.project(projectId) });
        void queries.invalidateQueries({ queryKey: keys.projects() });
      },
    },
  );
}

/** "Fix 3 things before you submit", each a link that opens the right milestone and focuses the field. */
function IssueSummary({ issues, onGo }: { issues: readonly Issue[]; onGo: (issue: Issue) => void }) {
  return (
    <div
      tabIndex={-1}
      id="boq-issues"
      role="alert"
      className="rounded-card border-l-4 border-bad-fg bg-bad-bg px-5 py-4"
    >
      <p className="font-semibold text-ink">
        Fix {issues.length === 1 ? "1 thing" : `${issues.length} things`} before you submit
      </p>
      <ul className="mt-1 flex flex-col gap-1">
        {issues.slice(0, 12).map((i) => (
          <li key={`${i.field}-${i.label}`}>
            <a
              href={`#${i.field}`}
              onClick={(e) => {
                e.preventDefault();
                onGo(i);
              }}
              className="type-small font-semibold text-bad-fg underline"
            >
              {i.label}
            </a>
          </li>
        ))}
        {issues.length > 12 ? (
          <li className="type-small text-bad-fg">and {issues.length - 12} more</li>
        ) : null}
      </ul>
    </div>
  );
}

function Hint({ line, prices }: { line: DraftLine; prices: readonly IndexEntry[] }) {
  const hint = indexHint(line, prices);
  if (!line.description.trim()) return <span className="text-muted">–</span>;
  if (hint.kind === "none") return <span className="text-muted">Not in the index</span>;
  if (hint.kind === "unit_differs") {
    return (
      <span className="text-slate">
        Index is per {hint.index.unit}
        <span className="block text-muted">Not compared</span>
      </span>
    );
  }
  const price = `Index ${formatMoney(hint.index.price_minor, "NGN")} / ${hint.index.unit}`;
  if (hint.percent === null) return <span className="text-slate">{price}</span>;
  const pct = `${hint.percent.startsWith("-") ? "" : "+"}${hint.percent}%`;
  return (
    <span className="flex flex-col items-start gap-1 text-slate">
      {price}
      {hint.over ? (
        <ToneChip label={`${pct} · will be flagged`} tone="warn" size="small" />
      ) : (
        <ToneChip label={`${pct} · close to the index`} tone="neutral" size="small" />
      )}
    </span>
  );
}

function LineRow({
  milestone,
  mIndex,
  line,
  lIndex,
  milestones,
  prices,
  problems,
  onChange,
  onRemove,
  onMove,
}: {
  milestone: DraftMilestone;
  mIndex: number;
  line: DraftLine;
  lIndex: number;
  milestones: readonly DraftMilestone[];
  prices: readonly IndexEntry[];
  problems: ReadonlyMap<string, string>;
  onChange: (patch: Partial<DraftLine>) => void;
  onRemove: () => void;
  onMove: (to: string) => void;
}) {
  const no = `${mIndex + 1}.${lIndex + 1}`;
  const total = lineTotal(line);
  const input = (part: "description" | "unit" | "quantity" | "price", label: string, numeric = false) => {
    const id = fieldId.line(line, part);
    const problem = problems.get(id);
    return (
      <div className="flex flex-col gap-1">
        <label htmlFor={id} className="type-small font-semibold text-ink lg:sr-only">
          {label} <span className="sr-only">, line {no}</span>
        </label>
        <input
          id={id}
          value={line[part]}
          onChange={(e) => onChange({ [part]: e.target.value })}
          inputMode={numeric ? "decimal" : undefined}
          list={part === "unit" ? "boq-units" : undefined}
          maxLength={part === "description" ? LIMITS.description : part === "unit" ? LIMITS.unit : 20}
          aria-invalid={problem ? true : undefined}
          aria-describedby={problem ? `${id}-problem` : undefined}
          className={cn(
            "min-h-11 w-full rounded-control border bg-white px-3 text-ink",
            numeric && "ibh-tabular text-right",
            problem ? "border-bad-fg" : "border-line-strong",
          )}
        />
        {problem ? (
          <p id={`${id}-problem`} className="type-small text-bad-fg">
            {problem}
          </p>
        ) : null}
      </div>
    );
  };
  return (
    <li className="ibh-boq-line grid gap-3 border-b border-line py-4 last:border-b-0 lg:items-start lg:gap-2">
      <span className="type-mono pt-3 text-slate">{no}</span>
      <div className="flex flex-col gap-2">
        {input("description", "Description")}
        <div className="flex flex-wrap items-center gap-2">
          {milestones.length > 1 ? (
            <>
              <label htmlFor={`${line.key}-move`} className="sr-only">
                Move line {no} to another milestone
              </label>
              <select
                id={`${line.key}-move`}
                value=""
                onChange={(e) => e.target.value && onMove(e.target.value)}
                className="type-small min-h-target rounded-control border border-line bg-white px-2 text-slate"
              >
                <option value="">Move to…</option>
                {milestones
                  .filter((m) => m.key !== milestone.key)
                  .map((m) => (
                    <option key={m.key} value={m.key}>
                      {milestones.indexOf(m) + 1} · {m.name.trim() || "Unnamed milestone"}
                    </option>
                  ))}
              </select>
            </>
          ) : null}
          <Button type="button" variant="text" onClick={onRemove} aria-label={`Remove line ${no}`}>
            <Trash2 aria-hidden strokeWidth={1.75} className="size-4" />
            Remove
          </Button>
        </div>
      </div>
      {input("unit", "Unit")}
      {input("quantity", "Quantity", true)}
      {input("price", "Unit price ₦", true)}
      <p className="ibh-tabular flex justify-between gap-2 font-semibold text-ink lg:block lg:pt-3 lg:text-right">
        <span className="type-small font-semibold text-slate lg:sr-only">Line total</span>
        {total === null ? <span className="text-muted">–</span> : formatMoney(total, "NGN")}
      </p>
      <div className="type-small lg:pt-3">
        <span className="font-semibold text-slate lg:sr-only">Price index: </span>
        <Hint line={line} prices={prices} />
      </div>
    </li>
  );
}

function Editor({
  projectId,
  boq,
  revising,
  onCancel,
}: {
  projectId: string;
  boq: Boq;
  revising: boolean;
  /** Back to the submitted BoQ: after cancelling a revision, or once the revision is sent. */
  onCancel: (() => void) | null;
}) {
  const [draft, setDraft] = useState<Draft>(() => readStored(projectId) ?? draftFrom(boq));
  const [restored] = useState(() => readStored(projectId) !== null);
  const [selected, setSelected] = useState(() => draft.milestones[0]!.key);
  const [checked, setChecked] = useState(false);
  const [dirty, setDirty] = useState(false);
  const index = usePriceIndex();
  const prices = useMemo(() => (index.data ?? []) as IndexEntry[], [index.data]);
  const submit = useSubmitBoq(projectId);
  const approve = useApproveBoq(projectId);

  const issues = useMemo(() => findIssues(draft), [draft]);
  const problems = useMemo(
    () => new Map(checked ? issues.map((i) => [i.field, i.message] as const) : []),
    [checked, issues],
  );
  const current = draft.milestones.find((m) => m.key === selected) ?? draft.milestones[0]!;
  const currentIndex = draft.milestones.indexOf(current);
  const total = draftTotal(draft);
  const overBudget = total > BigInt(boq.budget_minor);

  useEffect(() => {
    if (!dirty) return;
    writeStored(projectId, draft);
    const warn = (e: BeforeUnloadEvent) => e.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty, draft, projectId]);

  const update = (fn: (d: Draft) => Draft) => {
    setDraft(fn);
    setDirty(true);
  };
  const updateMilestone = (key: string, fn: (m: DraftMilestone) => DraftMilestone) =>
    update((d) => ({ milestones: d.milestones.map((m) => (m.key === key ? fn(m) : m)) }));

  const goTo = (issue: Issue) => {
    setSelected(issue.milestone);
    window.requestAnimationFrame(() => document.getElementById(issue.field)?.focus());
  };

  const send = () => {
    setChecked(true);
    if (issues.length) {
      window.requestAnimationFrame(() => document.getElementById("boq-issues")?.focus());
      return;
    }
    submit.mutate(toSubmit(draft), {
      onSuccess: () => {
        writeStored(projectId, null);
        setDirty(false);
        approve.mutate(null, { onSuccess: () => onCancel?.() });
      },
    });
  };

  const failure = submit.error ? toUiState(submit.error) : null;
  const errorCount = (key: string) => (checked ? issues.filter((i) => i.milestone === key).length : 0);

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-4">
      <datalist id="boq-units">
        {COMMON_UNITS.map((u) => (
          <option key={u} value={u} />
        ))}
      </datalist>

      <nav aria-label="Milestones in this BoQ" className="flex flex-col gap-3 lg:col-span-1">
        <p className="type-caption text-muted uppercase">Milestones</p>
        <ol className="flex flex-col gap-2">
          {draft.milestones.map((m, i) => {
            const count = errorCount(m.key);
            const active = m.key === current.key;
            return (
              <li key={m.key}>
                <button
                  type="button"
                  aria-current={active ? "true" : undefined}
                  onClick={() => setSelected(m.key)}
                  className={cn(
                    "flex w-full flex-col gap-0.5 rounded-control border px-3 py-2.5 text-left",
                    active ? "border-accent bg-white" : "border-transparent hover:bg-mist",
                  )}
                >
                  <span className="flex items-start justify-between gap-2">
                    <span className="font-semibold text-ink">
                      {i + 1} · {m.name.trim() || "Unnamed milestone"}
                    </span>
                    {count ? <ToneChip label={`${count} to fix`} tone="bad" size="small" /> : null}
                  </span>
                  <span className="type-small ibh-tabular text-slate">
                    {m.lines.length} {m.lines.length === 1 ? "line" : "lines"} ·{" "}
                    {formatMoney(milestoneTotal(m), "NGN")}
                  </span>
                </button>
              </li>
            );
          })}
        </ol>
        {draft.milestones.length < LIMITS.milestones ? (
          <button
            type="button"
            onClick={() => {
              const m = emptyMilestone();
              update((d) => ({ milestones: [...d.milestones, m] }));
              setSelected(m.key);
              window.requestAnimationFrame(() => document.getElementById(fieldId.name(m))?.focus());
            }}
            className="flex min-h-target items-center gap-2 rounded-control border border-dashed border-line-strong px-3 font-semibold text-ink hover:bg-mist"
          >
            <Plus aria-hidden strokeWidth={1.75} className="size-4" /> Add milestone
          </button>
        ) : (
          <p className="type-small text-slate">A BoQ can have at most {LIMITS.milestones} milestones.</p>
        )}
        <p className="type-small text-slate">
          Every line sits in a milestone. Use “Move to” to change which one.
        </p>
      </nav>

      <section aria-labelledby="boq-heading" className="flex min-w-0 flex-col gap-5 lg:col-span-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 id="boq-heading" className="type-h2 text-ink">
            {revising ? "Revise the bill of quantities" : "Price the work"}
          </h2>
          <p className="type-small text-slate">
            {lineCount(draft)} {lineCount(draft) === 1 ? "line" : "lines"} · prices in naira
          </p>
        </div>

        {restored && !dirty ? (
          <Alert tone="info" title="Your unsent changes are back">
            They were kept in this browser.{" "}
            <button
              type="button"
              className="font-semibold text-accent underline"
              onClick={() => {
                writeStored(projectId, null);
                const fresh = draftFrom(boq);
                setDraft(fresh);
                setSelected(fresh.milestones[0]!.key);
              }}
            >
              Start again from the saved BoQ
            </button>
          </Alert>
        ) : null}
        {checked && issues.length ? <IssueSummary issues={issues} onGo={goTo} /> : null}
        {approve.error ? (
          <Alert tone="warn" title="Your BoQ was sent, but your approval wasn’t recorded">
            <button
              type="button"
              className="font-semibold text-accent underline"
              onClick={() => approve.mutate(null, { onSuccess: () => onCancel?.() })}
            >
              Approve it now
            </button>
          </Alert>
        ) : null}
        {failure ? (
          failure.kind === "conflict" ? (
            <Alert tone="warn" title="This BoQ can’t be changed any more">
              It was approved by everyone while you were editing, so the project has started.{" "}
              <Link
                href={`/c/projects/${projectId}/milestones`}
                className="font-semibold text-accent underline"
              >
                See the milestones
              </Link>
            </Alert>
          ) : failure.kind === "forbidden" ? (
            <Alert tone="bad" title="Only this project’s contractor can price it">
              Sign in with the phone number the client added.
            </Alert>
          ) : (
            <Alert tone="bad" title="Your BoQ wasn’t sent">
              Nothing was lost: your changes are still here. Try again.
            </Alert>
          )
        ) : null}

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="flex flex-col gap-1 rounded-card bg-mist p-4">
            <p className="type-small font-semibold text-ink">
              Lines total <span className="font-normal text-slate">(worked out by iBackHome)</span>
            </p>
            <p className="ibh-tabular type-h2 text-ink">{formatMoney(total, "NGN")}</p>
          </div>
          <div className="flex flex-col gap-1 rounded-card border border-line p-4">
            <p className="type-small font-semibold text-ink">Your client’s budget</p>
            <p className="ibh-tabular type-h2 text-ink">{formatMoney(boq.budget_minor, "NGN")}</p>
            {overBudget ? (
              <p className="type-small text-warn-fg">
                The lines are {formatMoney(total - BigInt(boq.budget_minor), "NGN")} over the budget. You can
                still submit; your client sees both figures before approving.
              </p>
            ) : null}
          </div>
        </div>

        <Card className="flex flex-col gap-4 p-5">
          <div className="flex flex-wrap items-end justify-between gap-3">
            <div className="flex min-w-60 flex-1 flex-col gap-1">
              <label htmlFor={fieldId.name(current)} className="type-small font-semibold text-ink">
                Milestone {currentIndex + 1} name
              </label>
              <input
                id={fieldId.name(current)}
                value={current.name}
                maxLength={LIMITS.name}
                placeholder="For example, Foundation"
                onChange={(e) => updateMilestone(current.key, (m) => ({ ...m, name: e.target.value }))}
                aria-invalid={problems.has(fieldId.name(current)) ? true : undefined}
                aria-describedby={
                  problems.has(fieldId.name(current)) ? `${fieldId.name(current)}-problem` : undefined
                }
                className={cn(
                  "min-h-12 rounded-control border bg-white px-3.5 text-ink",
                  problems.has(fieldId.name(current)) ? "border-bad-fg" : "border-line-strong",
                )}
              />
              {problems.get(fieldId.name(current)) ? (
                <p id={`${fieldId.name(current)}-problem`} className="type-small text-bad-fg">
                  {problems.get(fieldId.name(current))}
                </p>
              ) : null}
            </div>
            <p className="ibh-tabular text-ink">
              Milestone total{" "}
              <span className="font-semibold">{formatMoney(milestoneTotal(current), "NGN")}</span>
            </p>
            {draft.milestones.length > 1 ? (
              <Button
                type="button"
                variant="text"
                onClick={() => {
                  const rest = draft.milestones.filter((m) => m.key !== current.key);
                  update(() => ({ milestones: rest }));
                  setSelected(rest[Math.max(0, currentIndex - 1)]!.key);
                }}
              >
                Remove this milestone
              </Button>
            ) : null}
          </div>

          <div
            aria-hidden
            className="type-caption ibh-boq-line hidden border-b border-line pb-2 text-muted uppercase lg:grid lg:gap-2"
          >
            <span>No.</span>
            <span>Description</span>
            <span>Unit</span>
            <span className="text-right">Qty</span>
            <span className="text-right">Unit price ₦</span>
            <span className="text-right">Line total</span>
            <span>Price index</span>
          </div>
          <ul aria-label={`Lines in milestone ${currentIndex + 1}`}>
            {current.lines.map((line, li) => (
              <LineRow
                key={line.key}
                milestone={current}
                mIndex={currentIndex}
                line={line}
                lIndex={li}
                milestones={draft.milestones}
                prices={prices}
                problems={problems}
                onChange={(patch) =>
                  updateMilestone(current.key, (m) => ({
                    ...m,
                    lines: m.lines.map((l) => (l.key === line.key ? { ...l, ...patch } : l)),
                  }))
                }
                onRemove={() =>
                  updateMilestone(current.key, (m) => ({
                    ...m,
                    lines: m.lines.length > 1 ? m.lines.filter((l) => l.key !== line.key) : [emptyLine()],
                  }))
                }
                onMove={(to) =>
                  update((d) => ({
                    milestones: d.milestones.map((m) => {
                      if (m.key === current.key) {
                        const rest = m.lines.filter((l) => l.key !== line.key);
                        return { ...m, lines: rest.length ? rest : [emptyLine()] };
                      }
                      return m.key === to
                        ? { ...m, lines: [...m.lines.filter((l) => !isBlank(l)), line] }
                        : m;
                    }),
                  }))
                }
              />
            ))}
          </ul>
          <div className="flex flex-wrap items-center gap-4">
            <button
              type="button"
              disabled={lineCount(draft) >= LIMITS.lines}
              onClick={() => {
                const l = emptyLine();
                updateMilestone(current.key, (m) => ({ ...m, lines: [...m.lines, l] }));
                window.requestAnimationFrame(() =>
                  document.getElementById(fieldId.line(l, "description"))?.focus(),
                );
              }}
              className="flex min-h-target items-center gap-2 rounded-control border border-dashed border-line-strong px-3 font-semibold text-ink hover:bg-mist disabled:text-muted"
            >
              <Plus aria-hidden strokeWidth={1.75} className="size-4" /> Add line
            </button>
            <p className="type-small text-slate">
              Quantities can have up to 3 decimal places. The price index is a guide: a line more than{" "}
              {FLAG_PERCENT}% above it is flagged to your client, but never stops you submitting.
            </p>
          </div>
        </Card>

        <div className="flex flex-col gap-3 border-t border-line pt-5 sm:flex-row sm:items-center">
          <Button size="lg" loading={submit.isPending || approve.isPending} onClick={send}>
            {revising ? "Submit the revised BoQ" : "Submit for review"}
          </Button>
          <p className="type-small flex-1 text-slate">
            {checked && issues.length
              ? `Fix the ${issues.length === 1 ? "problem" : `${issues.length} problems`} first. `
              : ""}
            Submitting counts as your approval. Your client and iBackHome ops then review it.
          </p>
          {onCancel ? (
            <Button
              variant="secondary"
              size="lg"
              onClick={() => {
                writeStored(projectId, null);
                onCancel();
              }}
            >
              Keep the submitted BoQ
            </Button>
          ) : null}
        </div>
      </section>
    </div>
  );
}

export function SavedLines({ boq }: { boq: Boq }) {
  return (
    <div className="flex flex-col gap-4">
      {boq.milestones.map((m) => (
        <div key={m.sequence} className="flex flex-col gap-2">
          <h3 className="flex flex-wrap items-baseline justify-between gap-2">
            <span className="type-h3 text-ink">
              {m.sequence} · {m.name}
            </span>
            <span className="ibh-tabular text-ink">
              Milestone total <span className="font-semibold">{formatMoney(m.amount_minor, "NGN")}</span>
            </span>
          </h3>
          <Table caption={`${m.name} lines`}>
            <thead>
              <tr>
                <Th>No.</Th>
                <Th>Description</Th>
                <Th>Unit</Th>
                <Th numeric>Qty</Th>
                <Th numeric>Unit price</Th>
                <Th numeric>Line total</Th>
              </tr>
            </thead>
            <tbody>
              {m.items.map((l) => (
                <Tr key={l.id}>
                  <Td className="type-mono text-slate">
                    {m.sequence}.{l.line_no}
                  </Td>
                  <Td>{l.description}</Td>
                  <Td>{l.unit}</Td>
                  <Td numeric>{quantityText(l.quantity)}</Td>
                  <Td numeric>{formatMoney(l.unit_price_minor, "NGN")}</Td>
                  <Td numeric className="font-semibold">
                    {formatMoney(l.total_minor, "NGN")}
                  </Td>
                </Tr>
              ))}
            </tbody>
          </Table>
        </div>
      ))}
    </div>
  );
}

function Approvals({ boq }: { boq: Boq }) {
  const timeZone = useViewerTimeZone();
  return (
    <ul className="flex flex-col gap-2">
      {["contractor", "client", "ops"].map((role) => {
        const a = boq.approvals.find((x) => x.role === role);
        return (
          <li key={role} className="flex items-center justify-between gap-3">
            <span className="text-ink">{ROLE_NAMES[role]}</span>
            {a ? (
              <span className="type-small flex items-center gap-1.5 text-ok-fg">
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
  );
}

function InReview({ projectId, boq, onRevise }: { projectId: string; boq: Boq; onRevise: () => void }) {
  const [confirm, setConfirm] = useState(false);
  const approve = useApproveBoq(projectId);
  const mine = boq.approvals.some((a) => a.role === "contractor");
  const others = boq.approvals.filter((a) => a.role !== "contractor").length;
  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-3">
      <section aria-labelledby="boq-heading" className="flex min-w-0 flex-col gap-5 lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="boq-heading" className="type-h2 text-ink">
            Bill of quantities
          </h2>
          <ToneChip label="In review" tone="info" size="small" />
        </div>
        <Alert tone="info" title={mine ? "Submitted for review" : "Waiting for your approval"}>
          {mine
            ? "Your client and iBackHome ops are reviewing it. When all three have approved, the milestones are created and your client can fund the first one."
            : "Check the lines, then approve. Your client and iBackHome ops approve too."}
        </Alert>
        {approve.error ? (
          <Alert tone="bad" title="Your approval wasn’t saved">
            Try again.
          </Alert>
        ) : null}
        <SavedLines boq={boq} />
      </section>
      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Totals</CardLabel>
          <p className="flex justify-between gap-3 text-ink">
            Lines total{" "}
            <span className="ibh-tabular font-semibold">{formatMoney(boq.boq_total_minor, "NGN")}</span>
          </p>
          <p className="flex justify-between gap-3 text-slate">
            Client’s budget <span className="ibh-tabular">{formatMoney(boq.budget_minor, "NGN")}</span>
          </p>
        </Card>
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Approvals</CardLabel>
          <Approvals boq={boq} />
        </Card>
        {mine ? null : (
          <Button size="lg" loading={approve.isPending} onClick={() => approve.mutate(null)}>
            Approve this BoQ
          </Button>
        )}
        <Button size="lg" variant="outline" onClick={() => (others || mine ? setConfirm(true) : onRevise())}>
          Revise BoQ
        </Button>
        <ConfirmDialog
          open={confirm}
          onOpenChange={setConfirm}
          title="Revise the BoQ?"
          description="When you submit the changes, every approval is cleared, yours included, and your client and iBackHome ops review it again."
          confirmLabel="Revise BoQ"
          cancelLabel="Keep it as it is"
          onConfirm={() => {
            setConfirm(false);
            onRevise();
          }}
        />
      </aside>
    </div>
  );
}

function Locked({ projectId, boq }: { projectId: string; boq: Boq }) {
  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-6 sm:px-8 lg:grid-cols-3">
      <section aria-labelledby="boq-heading" className="flex min-w-0 flex-col gap-5 lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3">
          <h2 id="boq-heading" className="type-h2 text-ink">
            Bill of quantities
          </h2>
          <ToneChip label="Approved" tone="ok" size="small" />
        </div>
        <p className="type-small flex items-center gap-2 text-slate">
          <Lock aria-hidden strokeWidth={1.75} className="size-4" />
          Approved by you, your client and iBackHome ops, so it can’t be changed. Each milestone’s work is on
          the{" "}
          <Link href={`/c/projects/${projectId}/milestones`} className="font-semibold text-accent underline">
            Milestones tab
          </Link>
          .
        </p>
        <SavedLines boq={boq} />
      </section>
      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Totals</CardLabel>
          <p className="flex justify-between gap-3 text-ink">
            Lines total{" "}
            <span className="ibh-tabular font-semibold">{formatMoney(boq.boq_total_minor, "NGN")}</span>
          </p>
        </Card>
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Approvals</CardLabel>
          <Approvals boq={boq} />
        </Card>
      </aside>
    </div>
  );
}

export function ContractorBoq({ projectId }: { projectId: string }) {
  const boq = useBoq(projectId);
  const [revising, setRevising] = useState(false);

  if (boq.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-6 sm:px-8">
        <Loading label="Loading the bill of quantities">
          <Skeleton className="h-9 w-72" />
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  }
  if (boq.error || !boq.data) {
    if (boq.error instanceof ApiError && boq.error.status === 403) {
      return (
        <div className="mx-auto w-full max-w-3xl px-4 py-10">
          <Alert tone="bad" title="This isn’t one of your projects">
            Only the project’s contractor can price its BoQ.
          </Alert>
        </div>
      );
    }
    return <ServerErrorContent reference={null} onRetry={() => void boq.refetch()} />;
  }

  const data = boq.data;
  if (!SETTING_UP.has(data.project_status)) return <Locked projectId={projectId} boq={data} />;
  if (data.project_status === "draft") {
    return <Editor key="draft" projectId={projectId} boq={data} revising={false} onCancel={null} />;
  }
  return revising ? (
    <Editor key="revise" projectId={projectId} boq={data} revising onCancel={() => setRevising(false)} />
  ) : (
    <InReview projectId={projectId} boq={data} onRevise={() => setRevising(true)} />
  );
}
