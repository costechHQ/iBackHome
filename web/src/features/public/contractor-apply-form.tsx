"use client";

import { X } from "lucide-react";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { useWrite } from "@/common/api/use-write";
import { NIGERIAN_STATES } from "@/common/nigeria";
import { Alert } from "@/common/ui/alert";
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
  MAX_STATES,
  SPECIALTIES,
  toBody,
  validate,
  type ContractorBody,
  type ContractorValues,
  type Field,
  type Specialty,
} from "./contractor-apply";

// The application form on /contractors#application (ADR 0007, phase 1). It asks for registration numbers only
// where the contractor has them, and never a NIN: ops check the registration and both references first. The
// hidden "website" field is a honeypot for bots (the backend answers success and stores nothing).

type TextKey =
  | "businessName"
  | "contactName"
  | "phone"
  | "email"
  | "years"
  | "projects"
  | "cac"
  | "corbon"
  | "r1Name"
  | "r1Phone"
  | "r2Name"
  | "r2Phone";

export function ContractorApplyForm() {
  const [values, setValues] = useState<ContractorValues>(EMPTY_VALUES);
  const [tried, setTried] = useState(false);
  const write = useWrite((body: ContractorBody, key: string) =>
    call(
      api().POST("/api/v1/contractor-applications", {
        body,
        headers: { "Idempotency-Key": key },
      }),
    ),
  );

  const set = <K extends keyof ContractorValues>(key: K, value: ContractorValues[K]) =>
    setValues((v) => ({ ...v, [key]: value }));
  const text = (key: TextKey) =>
    ({
      value: values[key],
      onChange: (e: { target: { value: string } }) => set(key, e.target.value),
    }) as const;
  const toggle = (specialty: Specialty) =>
    set(
      "specialties",
      values.specialties.includes(specialty)
        ? values.specialties.filter((s) => s !== specialty)
        : [...values.specialties, specialty],
    );

  const problems = tried ? validate(values) : [];
  const error = (field: Field) => problems.find((p) => p.field === field)?.message ?? null;
  const failure = write.isError ? describeError(write.error) : null;
  const serverError = (field: Field) => (failure?.field === field ? failure.message : null);

  if (write.isSuccess) {
    return (
      <ApplySuccess>
        <p className="max-w-md text-slate">
          Thank you. We check your registration first, then call your references, then contact you at{" "}
          <strong className="text-ink">{values.email.trim()}</strong> or on your phone. A receipt is on its
          way to your email.
        </p>
        <p className="type-small max-w-md rounded-card bg-canvas px-4 py-3 text-slate">
          If we approve you, we may put your business forward when a client asks us to find a contractor.
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
  const addable = NIGERIAN_STATES.filter((s) => !values.states.includes(s));

  return (
    <div className="flex flex-col gap-8">
      <ApplyIntro
        title="Join as a contractor"
        lead="About five minutes. Have your registration numbers and two references to hand."
      />
      <form onSubmit={submit} noValidate aria-label="Contractor application" className={APPLY_CARD}>
        <ErrorSummary problems={summary} />
        {failure && !failure.field ? (
          <Alert tone="bad" title="We couldn’t send your application">
            {failure.message}
          </Alert>
        ) : null}

        <ApplyGroup step={1} title="About your business" first>
          <div className={APPLY_GRID}>
            <TextField
              id={FIELD_IDS.businessName}
              label="Business name"
              autoComplete="organization"
              className="sm:col-span-2"
              error={error("businessName")}
              {...text("businessName")}
            />
            <TextField
              id={FIELD_IDS.contactName}
              label="Contact person"
              autoComplete="name"
              error={error("contactName")}
              {...text("contactName")}
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
              className="sm:col-span-2"
              error={error("email") ?? serverError("email")}
              {...text("email")}
            />
            <TextField
              id={FIELD_IDS.years}
              label="Years in business"
              type="number"
              inputMode="numeric"
              min={0}
              max={80}
              error={error("years")}
              {...text("years")}
            />
            <TextField
              id={FIELD_IDS.projects}
              label="Projects completed"
              type="number"
              inputMode="numeric"
              min={0}
              max={10000}
              help="Roughly how many, as far as you can count"
              error={error("projects")}
              {...text("projects")}
            />
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={2}
          title="Where and what you build"
          hint="Clients ask us for a contractor in a state and for a kind of work. Tell us both."
        >
          <div className="flex flex-col gap-3">
            <SelectField
              id={FIELD_IDS.states}
              label="States you work in"
              help={`Add up to ${MAX_STATES}`}
              value=""
              disabled={values.states.length >= MAX_STATES}
              onChange={(e) => e.target.value && set("states", [...values.states, e.target.value])}
              error={error("states")}
            >
              <option value="">Add a state</option>
              {addable.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </SelectField>
            {values.states.length ? (
              <ul className="flex flex-wrap gap-2" aria-label="Chosen states">
                {values.states.map((s) => (
                  <li
                    key={s}
                    className="type-small flex items-center gap-1 rounded-pill border border-line bg-canvas py-1 pr-1 pl-3 text-ink"
                  >
                    {s}
                    <button
                      type="button"
                      aria-label={`Remove ${s}`}
                      onClick={() =>
                        set(
                          "states",
                          values.states.filter((x) => x !== s),
                        )
                      }
                      className="flex size-6 items-center justify-center rounded-pill hover:bg-white"
                    >
                      <X aria-hidden strokeWidth={1.75} className="size-4" />
                    </button>
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
          <div role="group" aria-labelledby="apply-specialties-label" className="flex flex-col gap-2">
            <p id="apply-specialties-label" className="type-small font-semibold text-ink">
              What you build
            </p>
            <div className="grid gap-2 sm:grid-cols-2">
              {SPECIALTIES.map(({ value, label }) => (
                <label
                  key={value}
                  htmlFor={`apply-specialty-${value}`}
                  className="flex items-center gap-3 rounded-control bg-canvas px-3 py-2.5 text-ink"
                >
                  <input
                    id={`apply-specialty-${value}`}
                    type="checkbox"
                    checked={values.specialties.includes(value)}
                    onChange={() => toggle(value)}
                    className="size-5 flex-none"
                  />
                  {label}
                </label>
              ))}
            </div>
            {error("specialties") ? <p className="type-small text-bad-fg">{error("specialties")}</p> : null}
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={3}
          title="Your registration"
          hint="Optional, but it speeds things up. If you give a number, we check it first, on the register of the body."
        >
          <div className={APPLY_GRID}>
            <TextField
              id={FIELD_IDS.cac}
              label="CAC RC number"
              autoComplete="off"
              help="If your business is registered with the CAC"
              error={error("cac")}
              {...text("cac")}
            />
            <TextField
              id={FIELD_IDS.corbon}
              label="CORBON number"
              autoComplete="off"
              help="If you are a registered builder"
              error={error("corbon")}
              {...text("corbon")}
            />
          </div>
        </ApplyGroup>

        <ApplyGroup
          step={4}
          title="Two references"
          hint="Clients or colleagues who know your work. We will call them, so tell them to expect it."
        >
          <div className={APPLY_GRID}>
            <TextField
              id={FIELD_IDS.r1Name}
              label="Reference 1: name"
              error={error("r1Name")}
              {...text("r1Name")}
            />
            <TextField
              id={FIELD_IDS.r1Phone}
              label="Reference 1: phone"
              type="tel"
              inputMode="tel"
              error={error("r1Phone") ?? serverError("r1Phone")}
              {...text("r1Phone")}
            />
            <TextField
              id={FIELD_IDS.r2Name}
              label="Reference 2: name"
              error={error("r2Name")}
              {...text("r2Name")}
            />
            <TextField
              id={FIELD_IDS.r2Phone}
              label="Reference 2: phone"
              type="tel"
              inputMode="tel"
              error={error("r2Phone") ?? serverError("r2Phone")}
              {...text("r2Phone")}
            />
          </div>
        </ApplyGroup>

        <ApplyConsent
          id={FIELD_IDS.consent}
          checked={values.consent}
          onChange={(v) => set("consent", v)}
          error={error("consent")}
        >
          I agree that iBackHome may contact me and my two references to check this application, and may show
          my business name, the states I work in and what I build to clients who ask us to find them a
          contractor.
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
