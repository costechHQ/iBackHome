"use client";

import { Info } from "lucide-react";
import Link from "next/link";
import { useId, useState, type ReactNode } from "react";

import { ApiError } from "@/common/api/errors";
import { useViewerTimeZone } from "@/common/layout/online";
import { OpsHeader } from "@/common/layout/ops-shell";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ConfirmDialog } from "@/common/ui/dialog";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card } from "@/common/ui/surfaces";

import {
  CHECK_LABELS,
  approvalBlockers,
  listText,
  registrationRequired,
  specialtyLabel,
  SUMMARY_MIN,
  type ContractorChecks,
} from "./contractors";
import { useContractorApplication, useDecideContractor, type ContractorApplication } from "./contractors-api";

// Contractor application at /ops/contractors/:id (ADR 0007, phase 1): the application from
// GET /contractor-applications/{id} and the decision (POST .../decision). Ops tick each check as they do it and
// write the profile summary clients will read. "Approve" stays locked until both references are ticked (and the
// registration, when a CAC or CORBON number was given) and the summary is long enough; the backend refuses
// otherwise (422 vetting_checks_incomplete). Rejecting needs a reason, which the applicant is emailed.

const STATUS: Record<string, { label: string; tone: "warn" | "ok" | "bad" }> = {
  pending: { label: "Waiting for ops", tone: "warn" },
  approved: { label: "Approved", tone: "ok" },
  rejected: { label: "Rejected", tone: "bad" },
};

function CheckBox({
  label,
  checked,
  disabled,
  onChange,
}: {
  label: string;
  checked: boolean;
  disabled: boolean;
  onChange: (value: boolean) => void;
}) {
  const id = useId();
  return (
    <label htmlFor={id} className="flex items-center gap-3 rounded-control bg-mist px-3 py-2 text-ink">
      <input
        id={id}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
        className="size-5 flex-none"
      />
      <span className="type-small font-semibold">{label}</span>
    </label>
  );
}

function Section({
  title,
  chip,
  children,
}: {
  title: string;
  chip?: { label: string; tone: "ok" | "warn" | "neutral" };
  children: ReactNode;
}) {
  return (
    <Card className="flex flex-col gap-3 p-4">
      <div className="flex items-center justify-between gap-3">
        <h2 className="font-semibold text-ink">{title}</h2>
        {chip ? <ToneChip label={chip.label} tone={chip.tone} size="small" /> : null}
      </div>
      {children}
    </Card>
  );
}

function Row({ label, value, mono }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <dl className="flex justify-between gap-3">
      <dt className="text-slate">{label}</dt>
      <dd className={cn("text-right font-semibold text-ink", mono && "type-mono")}>{value}</dd>
    </dl>
  );
}

function decisionError(error: unknown): string | null {
  if (!error) return null;
  if (error instanceof ApiError) {
    if (error.code === "role_conflict") {
      return "This phone number already belongs to a client, supervisor, supplier or ops account. Ask the applicant for another number, or reject.";
    }
    if (error.code === "contractor_suspended") return "This contractor’s account is suspended.";
    if (error.code === "vetting_checks_incomplete")
      return "Every required check must be ticked before approving.";
    if (error.code === "application_decided")
      return "Someone already decided this application. Reload the page.";
    if (error.code === "profile_exists") return "This contractor already has a profile.";
  }
  return "Try again.";
}

function Detail({ app }: { app: ContractorApplication }) {
  const timeZone = useViewerTimeZone();
  const reasonId = useId();
  const summaryId = useId();
  const notesId = useId();
  const pending = app.status === "pending";
  const [checks, setChecks] = useState<ContractorChecks>({
    registration_verified: app.registration_verified,
    reference_1_verified: app.reference_1_verified,
    reference_2_verified: app.reference_2_verified,
  });
  const [notes, setNotes] = useState(app.ops_notes ?? "");
  const [summary, setSummary] = useState("");
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const decide = useDecideContractor(app.id);
  const needsRegistration = registrationRequired(app);
  const blockers = approvalBlockers(app, checks, summary);
  const set = (name: keyof ContractorChecks) => (value: boolean) => setChecks({ ...checks, [name]: value });
  const referencesDone = [checks.reference_1_verified, checks.reference_2_verified].filter(Boolean).length;
  const status = STATUS[app.status] ?? { label: app.status, tone: "warn" as const };
  const failed = decisionError(decide.error);
  const body = { ...checks, notes: notes.trim() || null };

  return (
    <div className="grid gap-5 p-5 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        <Section title="The business">
          <Row label="Business" value={app.business_name} />
          <Row label="Contact" value={app.contact_name} />
          <Row label="States served" value={listText(app.states_served)} />
          <Row label="Kinds of work" value={listText(app.specialties, specialtyLabel)} />
          <Row label="Years in business" value={app.years_in_business} />
          <Row label="Projects completed (declared)" value={app.projects_completed} />
        </Section>

        <Section
          title="Registration"
          chip={
            !needsRegistration
              ? { label: "None given", tone: "neutral" }
              : checks.registration_verified
                ? { label: "Checked", tone: "ok" }
                : { label: "To check", tone: "warn" }
          }
        >
          <Row label="CAC RC number" value={app.cac_rc_number ?? "not given"} mono />
          <Row label="CORBON number" value={app.corbon_number ?? "not given"} mono />
          {needsRegistration ? (
            <CheckBox
              label={CHECK_LABELS.registration_verified}
              checked={checks.registration_verified}
              disabled={!pending}
              onChange={set("registration_verified")}
            />
          ) : (
            <p className="type-small text-slate">
              No number was given, so there is nothing to check. Approval rests on the references.
            </p>
          )}
        </Section>

        <Section
          title="References"
          chip={{ label: `${referencesDone} of 2 confirmed`, tone: referencesDone === 2 ? "ok" : "warn" }}
        >
          <p className="type-small text-slate">
            Call each one and confirm they know the business and its work.
          </p>
          {(
            [
              ["reference_1_verified", app.reference_1_name, app.reference_1_phone],
              ["reference_2_verified", app.reference_2_name, app.reference_2_phone],
            ] as const
          ).map(([name, who, phone]) => (
            <div key={name} className="flex flex-col gap-2 border-t border-line pt-3">
              <p className="text-ink">
                {who} · <span className="type-mono">{phone}</span>
              </p>
              <CheckBox
                label={CHECK_LABELS[name]}
                checked={checks[name]}
                disabled={!pending}
                onChange={set(name)}
              />
            </div>
          ))}
        </Section>

        <Section title="Your notes">
          <label htmlFor={notesId} className="type-small text-slate">
            What you looked at (kept on the application, for the record; never shown to clients).
          </label>
          <textarea
            id={notesId}
            rows={3}
            maxLength={2000}
            value={notes}
            disabled={!pending}
            onChange={(e) => setNotes(e.target.value)}
            className="rounded-control border border-line-strong bg-white px-3 py-2 text-ink disabled:bg-mist"
          />
        </Section>
      </div>

      <div className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-4">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-semibold text-ink">Decision</h2>
            <ToneChip label={status.label} tone={status.tone} size="small" />
          </div>
          {!pending ? (
            <p className="type-small text-slate">
              {app.status === "approved" ? "Approved" : "Rejected"}
              {app.decided_at ? ` ${formatDateTime(app.decided_at, timeZone)}` : ""}.
              {app.rejection_reason ? ` Reason: ${app.rejection_reason}` : ""} They can apply again at any
              time.
            </p>
          ) : (
            <>
              {failed ? (
                <Alert tone="bad" title="The decision wasn’t saved">
                  {failed}
                </Alert>
              ) : null}
              <div className="flex flex-col gap-1.5">
                <label htmlFor={summaryId} className="type-small font-semibold text-ink">
                  Profile summary{" "}
                  <span className="font-normal text-slate">
                    (clients read this; write it yourself, at least {SUMMARY_MIN} characters)
                  </span>
                </label>
                <textarea
                  id={summaryId}
                  rows={4}
                  maxLength={1000}
                  value={summary}
                  onChange={(e) => setSummary(e.target.value)}
                  className="rounded-control border border-line-strong bg-white px-3 py-2 text-ink"
                />
              </div>
              {blockers.length ? (
                <div className="type-small flex items-start gap-2 rounded-control bg-mist p-3 text-ink">
                  <Info aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
                  <div>
                    Approve stays locked. Still needed:
                    <ul className="mt-1 list-disc pl-4">
                      {blockers.map((b) => (
                        <li key={b}>{b}</li>
                      ))}
                    </ul>
                  </div>
                </div>
              ) : null}
              <Button
                size="lg"
                disabled={blockers.length > 0}
                loading={decide.isPending && decide.variables?.decision === "approved"}
                onClick={() => setConfirm(true)}
              >
                Approve contractor
              </Button>
              <div className="flex flex-col gap-1.5">
                <label htmlFor={reasonId} className="type-small font-semibold text-ink">
                  Reason{" "}
                  <span className="font-normal text-slate">
                    (emailed to the applicant; required to reject)
                  </span>
                </label>
                <textarea
                  id={reasonId}
                  rows={3}
                  maxLength={1000}
                  value={reason}
                  onChange={(e) => setReason(e.target.value)}
                  aria-invalid={problem ? true : undefined}
                  aria-describedby={problem ? `${reasonId}-problem` : undefined}
                  className={cn(
                    "rounded-control border bg-white px-3 py-2 text-ink",
                    problem ? "border-bad-fg" : "border-line-strong",
                  )}
                />
                {problem ? (
                  <p id={`${reasonId}-problem`} className="type-small text-bad-fg">
                    {problem}
                  </p>
                ) : null}
              </div>
              <Button
                variant="destructive"
                className="self-start"
                loading={decide.isPending && decide.variables?.decision === "rejected"}
                onClick={() => {
                  if (!reason.trim()) return setProblem("Say why, so the applicant knows what to fix.");
                  setProblem(null);
                  decide.mutate({ decision: "rejected", ...body, reason: reason.trim() });
                }}
              >
                Reject
              </Button>
              <p className="type-small text-slate">
                Decisions are logged in the audit log with your account.
              </p>
            </>
          )}
          <ConfirmDialog
            open={confirm}
            onOpenChange={setConfirm}
            title="Approve this contractor?"
            description="They get an account, appear in the directory, and may be put forward when a client asks us for a contractor. They are emailed."
            confirmLabel="Approve contractor"
            cancelLabel="Not yet"
            busy={decide.isPending}
            onConfirm={() =>
              decide.mutate(
                { decision: "approved", ...body, summary: summary.trim() },
                { onSettled: () => setConfirm(false) },
              )
            }
          />
        </Card>
        <Card className="flex flex-col gap-2 p-4">
          <p className="type-caption text-muted uppercase">Application</p>
          <dl className="type-small flex flex-col gap-1.5">
            {[
              ["Applied", formatDateTime(app.created_at, timeZone)],
              ["Last changed", formatDateTime(app.updated_at, timeZone)],
              ["Phone", app.phone],
              ["Email", app.email],
              ["Agreed to be listed", formatDateTime(app.consented_at, timeZone)],
            ].map(([k, v]) => (
              <div key={k} className="flex justify-between gap-3">
                <dt className="text-slate">{k}</dt>
                <dd className="text-right font-semibold text-ink">{v}</dd>
              </div>
            ))}
          </dl>
        </Card>
      </div>
    </div>
  );
}

export function ContractorDetail({
  applicationId,
  environment,
}: {
  applicationId: string;
  environment: string;
}) {
  const app = useContractorApplication(applicationId);
  const header = (
    <OpsHeader
      title={`${app.data?.business_name ?? "Application"} · contractor application`}
      environment={environment}
    />
  );
  if (app.isPending) {
    return (
      <>
        {header}
        <div className="p-5">
          <Loading label="Loading the application">
            <Skeleton className="h-96 w-full" />
          </Loading>
        </div>
      </>
    );
  }
  if (app.error instanceof ApiError && app.error.status === 404) return <NotFoundContent />;
  if (!app.data) {
    return (
      <>
        {header}
        <ServerErrorContent reference={null} onRetry={() => void app.refetch()} />
      </>
    );
  }
  return (
    <>
      {header}
      <div className="px-5 pt-4">
        <Link href="/ops/contractors" className="type-small font-semibold text-accent">
          ‹ Contractors
        </Link>
      </div>
      <Detail key={`${app.data.id}-${app.data.status}`} app={app.data} />
    </>
  );
}
