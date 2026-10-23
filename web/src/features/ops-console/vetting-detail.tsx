"use client";

import { Info, Link2 } from "lucide-react";
import Link from "next/link";
import { useId, useState, type ReactNode } from "react";

import { ApiError } from "@/common/api/errors";
import { shortId } from "@/common/api/queries";
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

import { useApplication, useVet, type Application } from "./supervision-api";
import { CHECK_LABELS, openChecks, type VettingChecks } from "./supervision";

// WEB-OPS-003 vetting detail at /ops/vetting/:id: the application from GET /supervisors/{id}/application
// (backend #78) and the decision (POST /supervisors/{id}/vetting). Ops tick each check as they do it;
// "Approve applicant" stays locked until all four are ticked (the backend refuses otherwise, 422
// vetting_checks_incomplete); rejecting needs a reason, which the applicant sees. Not built (PACKAGE-REPORT
// W-49): "Ask for more information" (no endpoint), the document and photo thumbnails, guarantors' "known for"
// and call attempts, the NIN's last four digits (the backend keeps only whether it matched), phone model, areas.

const STATUS: Record<string, { label: string; tone: "warn" | "ok" | "bad" }> = {
  pending: { label: "Waiting for ops", tone: "warn" },
  approved: { label: "Approved", tone: "ok" },
  rejected: { label: "Rejected", tone: "bad" },
};

function CheckBox({
  name,
  checked,
  disabled,
  onChange,
}: {
  name: keyof VettingChecks;
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
      <span className="type-small font-semibold">{CHECK_LABELS[name]}</span>
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

function Detail({ app }: { app: Application }) {
  const timeZone = useViewerTimeZone();
  const reasonId = useId();
  const pending = app.vetting_status === "pending";
  const [checks, setChecks] = useState<VettingChecks>({
    registration_verified: app.registration_verified,
    nin_verified: app.nin_verified,
    guarantor_1_verified: app.guarantor_1_verified,
    guarantor_2_verified: app.guarantor_2_verified,
  });
  const [reason, setReason] = useState("");
  const [problem, setProblem] = useState<string | null>(null);
  const [confirm, setConfirm] = useState(false);
  const vet = useVet(app.user_id);
  const open = openChecks(checks);
  const set = (name: keyof VettingChecks) => (value: boolean) => setChecks({ ...checks, [name]: value });
  const guarantorsDone = [checks.guarantor_1_verified, checks.guarantor_2_verified].filter(Boolean).length;
  const status = STATUS[app.vetting_status] ?? { label: app.vetting_status, tone: "warn" as const };
  const error = vet.error instanceof ApiError ? vet.error : vet.error ? "error" : null;

  return (
    <div className="grid gap-5 p-5 lg:grid-cols-3">
      <div className="flex flex-col gap-4 lg:col-span-2">
        <Section
          title="Professional registration"
          chip={
            checks.registration_verified
              ? { label: "Checked", tone: "ok" }
              : { label: "To check", tone: "warn" }
          }
        >
          <dl className="flex justify-between gap-3">
            <dt className="text-slate">Body and number</dt>
            <dd className="type-mono font-semibold text-ink">
              {app.registration_body} · {app.registration_no}
            </dd>
          </dl>
          <CheckBox
            name="registration_verified"
            checked={checks.registration_verified}
            disabled={!pending}
            onChange={set("registration_verified")}
          />
        </Section>

        <Section
          title="NIN"
          chip={checks.nin_verified ? { label: "Matched", tone: "ok" } : { label: "To check", tone: "warn" }}
        >
          <p className="type-small text-slate">
            Match the applicant’s name and date of birth with the NIN record. iBackHome keeps only whether it
            matched, not the number.
          </p>
          <CheckBox
            name="nin_verified"
            checked={checks.nin_verified}
            disabled={!pending}
            onChange={set("nin_verified")}
          />
        </Section>

        <Section
          title="Guarantors"
          chip={{ label: `${guarantorsDone} of 2 confirmed`, tone: guarantorsDone === 2 ? "ok" : "warn" }}
        >
          <p className="type-small text-slate">
            Call each one and confirm they know the applicant and vouch for them.
          </p>
          {(
            [
              ["guarantor_1_verified", app.guarantor_1],
              ["guarantor_2_verified", app.guarantor_2],
            ] as const
          ).map(([name, who]) => (
            <div key={name} className="flex flex-col gap-2 border-t border-line pt-3">
              <p className="text-ink">{who}</p>
              <CheckBox name={name} checked={checks[name]} disabled={!pending} onChange={set(name)} />
            </div>
          ))}
        </Section>

        <Section
          title="Declared relationships"
          chip={{
            label: app.related_contractors.length
              ? `${app.related_contractors.length} declared`
              : "None declared",
            tone: app.related_contractors.length ? "warn" : "neutral",
          }}
        >
          {app.related_contractors.length ? (
            <ul className="flex flex-col gap-2">
              {app.related_contractors.map((r) => (
                <li
                  key={r.contractor_phone}
                  className="type-small flex items-start gap-2 rounded-control border-l-4 border-warn-fg bg-warn-bg px-3 py-2 text-ink"
                >
                  <Link2 aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
                  <span>
                    <span className="font-semibold">
                      {r.relationship.charAt(0).toUpperCase() + r.relationship.slice(1)}
                    </span>{" "}
                    of the contractor on <span className="type-mono">{r.contractor_phone}</span>. If approved,
                    they can never be assigned to or spot-check that contractor’s projects; the system blocks
                    it.
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="type-small text-slate">
              The applicant declared no relatives who work as contractors.
            </p>
          )}
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
              {app.vetting_status === "approved" ? "Approved" : "Rejected"}
              {app.vetted_at ? ` ${formatDateTime(app.vetted_at, timeZone)}` : ""}.
              {app.rejection_reason ? ` Reason: ${app.rejection_reason}` : ""} If they apply again, the
              application comes back to the queue.
            </p>
          ) : (
            <>
              {error ? (
                <Alert tone="bad" title="The decision wasn’t saved">
                  {error instanceof ApiError && error.code === "vetting_checks_incomplete"
                    ? "Every check must be ticked before approving."
                    : "Try again."}
                </Alert>
              ) : null}
              {open.length ? (
                <p className="type-small flex items-start gap-2 rounded-control bg-mist p-3 text-ink">
                  <Info aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
                  Approve stays locked until every check is ticked: {open.length} to go.
                </p>
              ) : null}
              <Button
                size="lg"
                disabled={open.length > 0}
                loading={vet.isPending && vet.variables?.decision === "approved"}
                onClick={() => setConfirm(true)}
              >
                Approve applicant
              </Button>
              <div className="flex flex-col gap-1.5">
                <label htmlFor={reasonId} className="type-small font-semibold text-ink">
                  Reason{" "}
                  <span className="font-normal text-slate">(sent to the applicant; required to reject)</span>
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
                loading={vet.isPending && vet.variables?.decision === "rejected"}
                onClick={() => {
                  if (!reason.trim()) return setProblem("Say why, so the applicant knows what to fix.");
                  setProblem(null);
                  vet.mutate({ decision: "rejected", ...checks, reason: reason.trim() });
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
            title="Approve this supervisor?"
            description="They can then be assigned to projects and make spot checks, except on projects of contractors they declared as relatives."
            confirmLabel="Approve applicant"
            cancelLabel="Not yet"
            busy={vet.isPending}
            onConfirm={() =>
              vet.mutate({ decision: "approved", ...checks }, { onSettled: () => setConfirm(false) })
            }
          />
        </Card>
        <Card className="flex flex-col gap-2 p-4">
          <p className="type-caption text-muted uppercase">Application</p>
          <dl className="type-small flex flex-col gap-1.5">
            {[
              ["Applied", formatDateTime(app.submitted_at, timeZone)],
              ["Last changed", formatDateTime(app.updated_at, timeZone)],
              ["Phone", app.phone ?? "–"],
              ["Email", app.email ?? "–"],
              ["Account", app.account_status === "active" ? "Active" : "Suspended"],
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

export function VettingDetail({ supervisorId, environment }: { supervisorId: string; environment: string }) {
  const app = useApplication(supervisorId);
  const name = app.data?.full_name ?? `Applicant ${shortId(supervisorId)}`;
  const header = <OpsHeader title={`${name} · supervisor application`} environment={environment} />;
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
        <Link href="/ops/vetting" className="type-small font-semibold text-accent">
          ‹ Vetting queue
        </Link>
      </div>
      <Detail key={`${app.data.user_id}-${app.data.vetting_status}`} app={app.data} />
    </>
  );
}
