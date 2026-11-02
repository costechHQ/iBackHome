"use client";

import { ClipboardList } from "lucide-react";
import { useId, useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Card, EmptyState } from "@/common/ui/surfaces";

import { useChecklistTemplates, useSaveChecklist, type ChecklistTemplate } from "./checklists-api";
import { itemsProblem, MAX_ITEMS, parseItems } from "./checklists";

// Checklists at /ops/checklists: what a supervisor checks, per kind of milestone (found by the milestone's
// name). Saving writes the list for new milestones of that name; milestones that already exist keep theirs.
// One item per line, in the order the supervisor sees them. Changes are audited by the backend.

function Editor({
  initialName,
  initialItems,
  lockName,
  onSaved,
}: {
  initialName: string;
  initialItems: string[];
  lockName: boolean;
  onSaved?: () => void;
}) {
  const nameId = useId();
  const itemsId = useId();
  const [name, setName] = useState(initialName);
  const [text, setText] = useState(initialItems.join("\n"));
  const [problem, setProblem] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const save = useSaveChecklist();
  const items = parseItems(text);
  const failed = save.error instanceof ApiError ? save.error : save.error ? "error" : null;

  return (
    <form
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        const trimmed = name.trim();
        const why = !trimmed
          ? "Say which kind of milestone this is for, for example Foundation."
          : itemsProblem(items);
        setProblem(why);
        setSaved(false);
        if (why) return;
        save.mutate(
          { milestone_name: trimmed, items },
          {
            onSuccess: () => {
              setSaved(true);
              onSaved?.();
            },
          },
        );
      }}
    >
      <div className="flex flex-col gap-1.5">
        <label htmlFor={nameId} className="type-small font-semibold text-ink">
          Milestone name
        </label>
        <input
          id={nameId}
          value={name}
          readOnly={lockName}
          maxLength={120}
          onChange={(e) => setName(e.target.value)}
          className="min-h-target rounded-control border border-line-strong bg-white px-3 text-ink read-only:bg-mist"
        />
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor={itemsId} className="type-small font-semibold text-ink">
          What the supervisor checks{" "}
          <span className="font-normal text-slate">
            (one per line, up to {MAX_ITEMS}; {items.length} now)
          </span>
        </label>
        <textarea
          id={itemsId}
          rows={Math.min(Math.max(items.length + 1, 4), 10)}
          value={text}
          onChange={(e) => setText(e.target.value)}
          aria-invalid={problem ? true : undefined}
          className="rounded-control border border-line-strong bg-white px-3 py-2 text-ink"
        />
      </div>
      {problem ? (
        <p role="alert" className="type-small text-bad-fg">
          {problem}
        </p>
      ) : null}
      {failed ? (
        <Alert tone="bad" title="The checklist wasn’t saved">
          {failed !== "error" && failed.status === 422
            ? "Check the name and the items, then try again."
            : "Try again."}
        </Alert>
      ) : null}
      {saved ? (
        <p role="status" className="type-small text-ok-fg">
          Saved. New milestones with this name get this list.
        </p>
      ) : null}
      <Button type="submit" className="self-start" loading={save.isPending}>
        Save checklist
      </Button>
    </form>
  );
}

function Template({ t }: { t: ChecklistTemplate }) {
  const timeZone = useViewerTimeZone();
  const [open, setOpen] = useState(false);
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-semibold text-ink">{t.milestone_name}</h2>
          <p className="type-small text-slate">
            {t.items.length} items · changed {formatDateTime(t.updated_at, timeZone)}
          </p>
        </div>
        <Button variant="outline" onClick={() => setOpen(!open)} aria-expanded={open}>
          {open ? "Close" : "Edit"}
        </Button>
      </div>
      {open ? (
        <Editor initialName={t.milestone_name} initialItems={t.items} lockName />
      ) : (
        <ol className="type-small list-decimal pl-5 text-ink">
          {t.items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ol>
      )}
    </Card>
  );
}

export function Checklists({ environment }: { environment: string }) {
  const list = useChecklistTemplates();
  const [adding, setAdding] = useState(false);
  const header = <OpsHeader title="Checklists" environment={environment} />;

  if (list.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the checklists">
            <Skeleton className="h-64 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (!list.data) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void list.refetch()} />
      </>
    );
  }
  return (
    <>
      {header}
      <div className="flex max-w-3xl flex-col gap-4 p-5">
        <p className="type-small text-slate">
          What a supervisor checks, per kind of milestone, found by the milestone’s name (case and spacing
          don’t matter). A saved list goes to milestones made afterwards; milestones that already exist keep
          theirs. A kind with no list uses the generic four items.
        </p>
        {list.data.length === 0 ? (
          <Card>
            <EmptyState icon={ClipboardList} title="No checklists yet">
              Every milestone uses the generic four-item list until you add one.
            </EmptyState>
          </Card>
        ) : (
          list.data.map((t) => <Template key={t.milestone_name} t={t} />)
        )}
        {adding ? (
          <Card className="flex flex-col gap-3 p-4">
            <h2 className="font-semibold text-ink">New checklist</h2>
            <Editor initialName="" initialItems={[]} lockName={false} onSaved={() => setAdding(false)} />
          </Card>
        ) : (
          <Button variant="outline" className="self-start" onClick={() => setAdding(true)}>
            Add a checklist
          </Button>
        )}
      </div>
    </>
  );
}
