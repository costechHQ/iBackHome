"use client";

import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { useWrite } from "@/common/api/use-write";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ErrorSummary, SelectField, TextField } from "@/common/ui/field";

import {
  APPLY_CARD,
  APPLY_GRID,
  ApplyConsent,
  ApplyGroup,
  ApplyHoneypot,
  ApplyIntro,
  ApplySubmit,
  ApplySuccess,
} from "./apply-parts";
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
      <ApplySuccess>
        <p className="max-w-md text-slate">
          Thank you. We check your registration number first, then call your guarantors, then contact you at{" "}
          <strong className="text-ink">{values.email.trim()}</strong> or on your phone. A receipt is on its
          way to your email.
        </p>
        <p className="type-small max-w-md rounded-card bg-canvas px-4 py-3 text-slate">
          Please don’t send your NIN until we ask for it.
        </p>
      </ApplySuccess>
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
    <div className="flex flex-col gap-8">
      <ApplyIntro title="Your application" lead="About five minutes. Have your certificate to hand." />
      <form onSubmit={submit} noValidate aria-label="Supervisor application" className={APPLY_CARD}>
        <ErrorSummary problems={summary} />
        {failure && !failure.field ? (
          <Alert tone="bad" title="We couldn’t send your application">
            {failure.message}
          </Alert>
        ) : null}

        <ApplyGroup step={1} title="About you" first>
          <div className={APPLY_GRID}>
            <TextField
              id={FIELD_IDS.fullName}
              label="Full name"
              autoComplete="name"
              className="sm:col-span-2"
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
              help="Your receipt and our replies come here"
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
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={2}
          title="Your professional registration"
          hint="We check this first, on the register of the body you name. We ask for your NIN later, only if it checks out."
        >
          <div className={APPLY_GRID}>
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
              id={FIELD_IDS.years}
              label="Years of experience"
              type="number"
              inputMode="numeric"
              min={0}
              max={60}
              error={error("years")}
              {...text("years")}
            />
            <TextField
              id={FIELD_IDS.registrationNo}
              label="Registration number"
              className="sm:col-span-2"
              autoComplete="off"
              help="Exactly as on your certificate, for example R.98765"
              error={error("registrationNo")}
              {...text("registrationNo")}
            />
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={3}
          title="Two guarantors"
          hint="People who know you and your work. We will call them, so tell them to expect it."
        >
          <div className={APPLY_GRID}>
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
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={4}
          title="Relatives who work as contractors"
          hint="Optional. Declaring them protects you: you’ll never be assigned to, or spot-check, their projects."
        >
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
        </ApplyGroup>

        <ApplyConsent
          id={FIELD_IDS.consent}
          checked={values.consent}
          onChange={(v) => set("consent", v)}
          error={error("consent")}
        >
          I agree that iBackHome may contact me and my two guarantors to check this application.
        </ApplyConsent>

        <ApplyHoneypot value={values.website} onChange={(v) => set("website", v)} />

        <ApplySubmit
          pending={write.isPending}
          note="Used only to check your application. No NIN is asked for here."
        />
      </form>
    </div>
  );
}
