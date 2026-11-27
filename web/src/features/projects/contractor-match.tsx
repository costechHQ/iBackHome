"use client";

import Link from "next/link";
import { useId, useState, type ReactNode } from "react";

import { useMatchRequest, useProject, type ContractorCard, type MatchRequest } from "@/common/api/queries";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { formatMoney } from "@/common/money";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ConfirmDialog } from "@/common/ui/dialog";
import { SelectField, TextField } from "@/common/ui/field";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

import { useCancelMatch, useChooseContractor, useRequestMatch } from "./matching-api";
import {
  describeMatchError,
  EMPTY_BRIEF,
  NOTES_MAX,
  STATUS_COPY,
  toBrief,
  validateBrief,
  WORK_TYPES,
  workTypeLabel,
  type BriefField,
  type BriefValues,
  type MatchStatus,
} from "./matching";

// Find a contractor at /projects/:id/contractor (ADR 0007, phase 2). A client with a draft project and no
// contractor asks for one; our team shortlist up to three vetted contractors after phoning them; the client
// chooses, and the contractor is added to the project. A contractor's phone number and email are never shown
// here: only a card (name, summary, states, kinds of work, years, projects).

function Shell({ projectId, children }: { projectId: string; children: ReactNode }) {
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-5 px-4 py-6 sm:px-10">
      <Link href={`/projects/${projectId}/setup`} className="type-small font-semibold text-accent">
        ‹ Set-up
      </Link>
      <h1 className="type-h2 text-ink">Find a contractor</h1>
      {children}
    </div>
  );
}

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

function BriefSummary({ request }: { request: MatchRequest }) {
  return (
    <Facts
      rows={[
        ["Where", `${request.city}, ${request.state}`],
        ["Kind of work", workTypeLabel(request.work_type)],
        ["When", request.timeline],
        ["Budget", formatMoney(request.budget_minor, request.currency)],
        ...(request.notes ? ([["Notes", request.notes]] as const) : []),
      ]}
    />
  );
}

// --- No request yet: the brief --------------------------------------------------------------------------

function BriefForm({ projectId, cancelledBefore }: { projectId: string; cancelledBefore: boolean }) {
  const ids = { notes: useId() };
  const [values, setValues] = useState<BriefValues>(EMPTY_BRIEF);
  const [problems, setProblems] = useState<Partial<Record<BriefField, string>>>({});
  const request = useRequestMatch(projectId);
  const set = <K extends keyof BriefValues>(key: K, value: BriefValues[K]) =>
    setValues((v) => ({ ...v, [key]: value }));

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (request.isPending) return;
    const next = validateBrief(values);
    setProblems(next);
    if (Object.keys(next).length) return;
    request.mutate(toBrief(values));
  }

  return (
    <Card className="flex flex-col gap-5 p-6 sm:p-8">
      <div className="flex flex-col gap-1">
        <h2 className="type-h3 text-ink">What are you looking for?</h2>
        <p className="text-slate">
          Tell us where and what. Our team will phone a few vetted contractors and put up to three forward,
          and you choose. It costs nothing.
        </p>
      </div>
      {cancelledBefore ? (
        <Alert tone="info">Your earlier request was cancelled. You can send a new one.</Alert>
      ) : null}
      {request.isError ? <Alert tone="bad" title={describeMatchError(request.error)} /> : null}
      <form noValidate onSubmit={submit} className="flex flex-col gap-5" aria-label="Contractor request">
        <div className="grid gap-5 sm:grid-cols-2">
          <SelectField
            label="State"
            value={values.state}
            onChange={(e) => set("state", e.target.value)}
            error={problems.state}
          >
            <option value="">Choose the state</option>
            {NIGERIAN_STATES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </SelectField>
          <TextField
            label="City or town"
            autoComplete="address-level2"
            value={values.city}
            onChange={(e) => set("city", e.target.value)}
            error={problems.city}
          />
          <SelectField
            label="Kind of work"
            value={values.workType}
            onChange={(e) => set("workType", e.target.value as BriefValues["workType"])}
            error={problems.workType}
          >
            <option value="">Choose one</option>
            {WORK_TYPES.map((w) => (
              <option key={w.value} value={w.value}>
                {w.label}
              </option>
            ))}
          </SelectField>
          <TextField
            label="When do you want to start?"
            help="For example: within three months"
            maxLength={200}
            value={values.timeline}
            onChange={(e) => set("timeline", e.target.value)}
            error={problems.timeline}
          />
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.notes} className="type-small font-semibold text-ink">
            Anything else we should know? <span className="font-normal text-slate">(optional)</span>
          </label>
          <textarea
            id={ids.notes}
            rows={4}
            maxLength={NOTES_MAX}
            value={values.notes}
            onChange={(e) => set("notes", e.target.value)}
            aria-invalid={problems.notes ? true : undefined}
            className={cn(
              "rounded-control border bg-white px-3.5 py-3 text-ink",
              problems.notes ? "border-bad-fg" : "border-line-strong",
            )}
          />
          {problems.notes ? <p className="type-small text-bad-fg">{problems.notes}</p> : null}
        </div>
        <p className="type-small text-slate">
          We use your project&apos;s budget, so you don&apos;t need to enter it again. Your contact details
          are never given to a contractor until you choose them.
        </p>
        <Button type="submit" size="lg" loading={request.isPending} className="self-start">
          Ask for a contractor
        </Button>
      </form>
    </Card>
  );
}

// --- A shortlist ---------------------------------------------------------------------------------------------

function ContractorCardView({
  card,
  onChoose,
  chosen = false,
}: {
  card: ContractorCard;
  onChoose?: () => void;
  chosen?: boolean;
}) {
  return (
    <Card className="flex flex-col gap-3 p-5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="type-h3 text-ink">{card.business_name}</h3>
        <ToneChip label="Vetted by iBackHome" tone="ok" size="small" />
      </div>
      <p className="text-slate">{card.summary}</p>
      <Facts
        rows={[
          ["Works in", card.states_served.join(", ")],
          ["Kinds of work", card.specialties.map(workTypeLabel).join(", ")],
          ["Years in business", card.years_in_business],
          ["Projects completed", card.projects_completed],
        ]}
      />
      {onChoose ? (
        <Button onClick={onChoose} className="self-start">
          Choose {card.business_name}
        </Button>
      ) : chosen ? (
        <ToneChip label="Your contractor" tone="ok" size="small" />
      ) : null}
    </Card>
  );
}

function Shortlist({ projectId, request }: { projectId: string; request: MatchRequest }) {
  const [picked, setPicked] = useState<ContractorCard | null>(null);
  const choose = useChooseContractor(projectId, request.id);
  const cancel = useCancelMatch(projectId, request.id);
  const [confirmCancel, setConfirmCancel] = useState(false);
  const failure = choose.isError ? choose.error : cancel.isError ? cancel.error : null;
  return (
    <>
      <Card className="flex flex-col gap-3 p-5">
        <div className="flex items-center justify-between gap-3">
          <h2 className="font-semibold text-ink">Your request</h2>
          <ToneChip label={STATUS_COPY.shortlisted.label} tone="ok" size="small" />
        </div>
        <BriefSummary request={request} />
      </Card>
      <p className="text-slate">
        We phoned each of these contractors and checked they are free and interested. Read about them and
        choose the one you want. You can only choose one.
      </p>
      {failure ? <Alert tone="bad" title={describeMatchError(failure)} /> : null}
      <div className="flex flex-col gap-4">
        {request.shortlist.map((card) => (
          <ContractorCardView key={card.id} card={card} onChoose={() => setPicked(card)} />
        ))}
      </div>
      <Button variant="outline" className="self-start" onClick={() => setConfirmCancel(true)}>
        Cancel this request
      </Button>
      <ConfirmDialog
        open={picked !== null}
        onOpenChange={(open) => !open && setPicked(null)}
        title={`Choose ${picked?.business_name ?? "this contractor"}?`}
        description="They are added to your project and told. They sign in with their phone number and price the work in a bill of quantities, which you then review."
        confirmLabel="Choose this contractor"
        cancelLabel="Not yet"
        busy={choose.isPending}
        onConfirm={() => picked && choose.mutate(picked.id, { onSettled: () => setPicked(null) })}
      />
      <ConfirmDialog
        open={confirmCancel}
        onOpenChange={setConfirmCancel}
        title="Cancel this request?"
        description="Our team will stop looking. You can send a new request any time while the project is being set up."
        confirmLabel="Cancel the request"
        cancelLabel="Keep it"
        destructive
        busy={cancel.isPending}
        onConfirm={() => cancel.mutate(null, { onSettled: () => setConfirmCancel(false) })}
      />
    </>
  );
}

function Waiting({ projectId, request }: { projectId: string; request: MatchRequest }) {
  const cancel = useCancelMatch(projectId, request.id);
  const [confirm, setConfirm] = useState(false);
  return (
    <>
      <Card className="flex flex-col gap-4 p-6 sm:p-8">
        <div className="flex items-center justify-between gap-3">
          <h2 className="type-h3 text-ink">{STATUS_COPY.open.label}</h2>
          <ToneChip label="Open" tone="warn" size="small" />
        </div>
        <p className="text-slate">
          Our team is phoning vetted contractors in {request.state} to check they are free and interested.
          We&apos;ll tell you as soon as your shortlist is ready.
        </p>
        <BriefSummary request={request} />
        {cancel.isError ? <Alert tone="bad" title={describeMatchError(cancel.error)} /> : null}
        <Button variant="outline" className="self-start" onClick={() => setConfirm(true)}>
          Cancel this request
        </Button>
      </Card>
      <ConfirmDialog
        open={confirm}
        onOpenChange={setConfirm}
        title="Cancel this request?"
        description="Our team will stop looking. You can send a new request any time while the project is being set up."
        confirmLabel="Cancel the request"
        cancelLabel="Keep it"
        destructive
        busy={cancel.isPending}
        onConfirm={() => cancel.mutate(null, { onSettled: () => setConfirm(false) })}
      />
    </>
  );
}

function Matched({ projectId, request }: { projectId: string; request: MatchRequest }) {
  return (
    <>
      <Alert tone="ok" title={`You chose ${request.chosen?.business_name ?? "a contractor"}`}>
        They have been added to your project and told. Next they price the work, and you review it.
      </Alert>
      {request.chosen ? <ContractorCardView card={request.chosen} chosen /> : null}
      <Button asChild className="self-start">
        <Link href={`/projects/${projectId}/setup`}>Back to set-up</Link>
      </Button>
    </>
  );
}

export function ContractorMatch({ projectId }: { projectId: string }) {
  const project = useProject(projectId);
  const request = useMatchRequest(projectId);

  if (project.isPending || request.isPending) {
    return (
      <Shell projectId={projectId}>
        <Loading label="Loading your request">
          <Skeleton className="h-64 w-full" />
        </Loading>
      </Shell>
    );
  }
  if (!project.data || request.isError) {
    return (
      <ServerErrorContent
        reference={null}
        onRetry={() => {
          void project.refetch();
          void request.refetch();
        }}
      />
    );
  }
  const p = project.data;
  const req = request.data;
  const status = req ? (req.status as MatchStatus) : null;

  if (status === "matched" && req) {
    return (
      <Shell projectId={projectId}>
        <Matched projectId={projectId} request={req} />
      </Shell>
    );
  }
  if (p.contractor_id) {
    return (
      <Shell projectId={projectId}>
        <Alert tone="info" title="Your project already has a contractor">
          You can only ask us to find a contractor before one has been added.
        </Alert>
      </Shell>
    );
  }
  if (p.status !== "draft") {
    return (
      <Shell projectId={projectId}>
        <Alert tone="info" title="This project is past set-up">
          A contractor can only be requested while the project is being set up.
        </Alert>
      </Shell>
    );
  }
  return (
    <Shell projectId={projectId}>
      {req && status === "open" ? <Waiting projectId={projectId} request={req} /> : null}
      {req && status === "shortlisted" ? <Shortlist projectId={projectId} request={req} /> : null}
      {!req || status === "cancelled" ? (
        <BriefForm projectId={projectId} cancelledBefore={status === "cancelled"} />
      ) : null}
    </Shell>
  );
}
