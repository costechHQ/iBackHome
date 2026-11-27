"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState, type ReactNode } from "react";

import { api, call } from "@/common/api/client";
import { useWrite } from "@/common/api/use-write";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ErrorSummary, SelectField, TextField } from "@/common/ui/field";

import {
  describeError,
  EMPTY_VALUES,
  FIELD_IDS,
  MAX_RELATIVES,
  REGISTRATION_BODIES,
  toBody,
  validate,
  type ApplyBody,
  type ApplyValues,
  type Field,
} from "./supervisor-apply";

// The application form on /supervisors#apply (ADR 0005, slice 1). It asks for the registration number, never
// the NIN: ops check the registration first and ask for the NIN only after. The hidden "website" field is a
// honeypot for bots (a person never sees it; the backend answers success and stores nothing).

function Group({ title, hint, children }: { title: string; hint?: string; children: ReactNode }) {
  return (
    <fieldset className="flex flex-col gap-4">
      <legend className="type-h3 text-ink">{title}</legend>
      {hint ? <p className="type-small -mt-2 text-slate">{hint}</p> : null}
      <div className="grid gap-4 sm:grid-cols-2">{children}</div>
    </fieldset>
  );
}

export function SupervisorApplyForm() {
  const [values, setValues] = useState<ApplyValues>(EMPTY_VALUES);
  const [tried, setTried] = useState(false);
  const write = useWrite((body: ApplyBody, key: string) =>
    call(
      api().POST("/api/v1/supervisor-applications", {
        body,
        headers: { "Idempotency-Key": key },
      }),
    ),
  );

  const set = <K extends keyof ApplyValues>(key: K, value: ApplyValues[K]) =>
    setValues((v) => ({ ...v, [key]: value }));
  const text = (
    key:
      | "fullName"
      | "phone"
      | "email"
      | "city"
      | "registrationNo"
      | "years"
      | "g1Name"
      | "g1Phone"
      | "g2Name"
      | "g2Phone",
  ) =>
    ({
      value: values[key],
      onChange: (e: { target: { value: string } }) => set(key, e.target.value),
    }) as const;

  const problems = tried ? validate(values) : [];
  const problem = problems.find.bind(problems);
  const error = (field: Field) => problem((p) => p.field === field)?.message ?? null;
  const failure = write.isError ? describeError(write.error) : null;
  const serverError = (field: Field) => (failure?.field === field ? failure.message : null);

  if (write.isSuccess) {
    return (
      <Alert tone="ok" title="Application received">
        <p>
          Thank you. We check your registration number first, then call your guarantors, then contact you at{" "}
          <strong>{values.email.trim()}</strong> or on your phone. A receipt is on its way to your email.
        </p>
        <p className="mt-2">Please don’t send your NIN until we ask for it.</p>
      </Alert>
    );
  }

  function submit(event: React.FormEvent) {
    event.preventDefault();
    if (write.isPending) return;
    setTried(true);
    if (validate(values).length > 0) return;
    write.mutate(toBody(values));
  }

  const summary = [
    ...problems.map((p) => ({ fieldId: FIELD_IDS[p.field], message: p.message })),
    ...(failure?.field ? [{ fieldId: FIELD_IDS[failure.field], message: failure.message }] : []),
  ];

  return (
    <form onSubmit={submit} noValidate className="flex flex-col gap-8" aria-label="Supervisor application">
      <ErrorSummary problems={summary} />
      {failure && !failure.field ? (
        <Alert tone="bad" title="We couldn’t send your application">
          {failure.message}
        </Alert>
      ) : null}

      <Group title="About you">
        <TextField
          id={FIELD_IDS.fullName}
          label="Full name"
          autoComplete="name"
          error={error("fullName")}
          {...text("fullName")}
        />
        <TextField
          id={FIELD_IDS.phone}
          label="Phone number"
          type="tel"
          autoComplete="tel"
          inputMode="tel"
          help="We can reach you here, and by WhatsApp"
          error={error("phone")}
          {...text("phone")}
        />
        <TextField
          id={FIELD_IDS.email}
          label="Email"
          type="email"
          autoComplete="email"
          error={error("email") ?? serverError("email")}
          {...text("email")}
        />
        <SelectField
          id={FIELD_IDS.state}
          label="State"
          value={values.state}
          onChange={(e) => set("state", e.target.value)}
          error={error("state")}
        >
          <option value="">Choose a state</option>
          {NIGERIAN_STATES.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </SelectField>
        <TextField
          id={FIELD_IDS.city}
          label="City or town"
          autoComplete="address-level2"
          error={error("city")}
          {...text("city")}
        />
      </Group>

      <Group
        title="Your professional registration"
        hint="We check this first, on the register of the body you name. We ask for your NIN later, only if it checks out."
      >
        <SelectField
          id={FIELD_IDS.registrationBody}
          label="Registration body"
          value={values.registrationBody}
          onChange={(e) => set("registrationBody", e.target.value as ApplyValues["registrationBody"])}
          error={error("registrationBody")}
        >
          <option value="">Choose one</option>
          {REGISTRATION_BODIES.map((b) => (
            <option key={b.value} value={b.value}>
              {b.label}
            </option>
          ))}
        </SelectField>
        <TextField
          id={FIELD_IDS.registrationNo}
          label="Registration number"
          autoComplete="off"
          help="Exactly as on your certificate, for example R.98765"
          error={error("registrationNo")}
          {...text("registrationNo")}
        />
        <TextField
          id={FIELD_IDS.years}
          label="Years of experience"
          type="number"
          inputMode="numeric"
          min={0}
          max={60}
          error={error("years")}
          {...text("years")}
        />
      </Group>

      <Group
        title="Two guarantors"
        hint="People who know you and your work. We will call them, so tell them to expect it."
      >
        <TextField
          id={FIELD_IDS.g1Name}
          label="Guarantor 1: name"
          error={error("g1Name")}
          {...text("g1Name")}
        />
        <TextField
          id={FIELD_IDS.g1Phone}
          label="Guarantor 1: phone"
          type="tel"
          inputMode="tel"
          error={error("g1Phone") ?? serverError("g1Phone")}
          {...text("g1Phone")}
        />
        <TextField
          id={FIELD_IDS.g2Name}
          label="Guarantor 2: name"
          error={error("g2Name")}
          {...text("g2Name")}
        />
        <TextField
          id={FIELD_IDS.g2Phone}
          label="Guarantor 2: phone"
          type="tel"
          inputMode="tel"
          error={error("g2Phone") ?? serverError("g2Phone")}
          {...text("g2Phone")}
        />
      </Group>

      <fieldset className="flex flex-col gap-4">
        <legend className="type-h3 text-ink">Relatives who work as contractors</legend>
        <p className="type-small -mt-2 text-slate">
          Optional. Declaring them protects you: you’ll never be assigned to, or spot-check, their projects.
        </p>
        {error("relatives") ? <p className="type-small text-bad-fg">{error("relatives")}</p> : null}
        {values.relatives.map((row, i) => (
          <div key={i} className="flex flex-col gap-4 sm:flex-row sm:items-end">
            <TextField
              id={`apply-relative-${i}-name`}
              className="flex-1"
              label={`Relative ${i + 1}: name`}
              value={row.name}
              onChange={(e) =>
                set(
                  "relatives",
                  values.relatives.map((r, j) => (j === i ? { ...r, name: e.target.value } : r)),
                )
              }
            />
            <TextField
              id={`apply-relative-${i}-phone`}
              className="flex-1"
              label={`Relative ${i + 1}: phone`}
              type="tel"
              inputMode="tel"
              value={row.phone}
              onChange={(e) =>
                set(
                  "relatives",
                  values.relatives.map((r, j) => (j === i ? { ...r, phone: e.target.value } : r)),
                )
              }
            />
            <Button
              type="button"
              variant="secondary"
              aria-label={`Remove relative ${i + 1}`}
              onClick={() =>
                set(
                  "relatives",
                  values.relatives.filter((_, j) => j !== i),
                )
              }
            >
              <Trash2 aria-hidden strokeWidth={1.75} className="size-5" />
            </Button>
          </div>
        ))}
        {values.relatives.length < MAX_RELATIVES ? (
          <Button
            type="button"
            variant="secondary"
            className="self-start"
            onClick={() => set("relatives", [...values.relatives, { name: "", phone: "" }])}
          >
            <Plus aria-hidden strokeWidth={1.75} className="size-5" />
            Add a relative
          </Button>
        ) : null}
      </fieldset>

      <div className="flex flex-col gap-2">
        <label htmlFor={FIELD_IDS.consent} className="flex items-start gap-3 text-ink">
          <input
            id={FIELD_IDS.consent}
            type="checkbox"
            checked={values.consent}
            onChange={(e) => set("consent", e.target.checked)}
            aria-invalid={error("consent") ? true : undefined}
            className="mt-1 size-5 flex-none"
          />
          <span>
            I agree that iBackHome may contact me and my two guarantors to check this application.{" "}
            <span className="text-muted">Required</span>
          </span>
        </label>
        {error("consent") ? <p className="type-small text-bad-fg">{error("consent")}</p> : null}
      </div>

      {/* Honeypot: off-screen, skipped by keyboards and screen readers. A bot that fills it is ignored. */}
      <div aria-hidden className="sr-only">
        <label>
          Leave this empty
          <input
            type="text"
            name="website"
            tabIndex={-1}
            autoComplete="off"
            value={values.website}
            onChange={(e) => set("website", e.target.value)}
          />
        </label>
      </div>

      <Button type="submit" size="lg" loading={write.isPending} className="self-start">
        {write.isPending ? "Sending…" : "Send my application"}
      </Button>
    </form>
  );
}
