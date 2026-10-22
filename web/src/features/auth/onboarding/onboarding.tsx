"use client";

import { useQuery } from "@tanstack/react-query";
import { CircleCheck, Check, Landmark, Lock } from "lucide-react";
import { useId, useMemo, useState, type ReactNode } from "react";

import { api, call } from "@/common/api/client";
import { ApiError, toUiState } from "@/common/api/errors";
import { useWrite } from "@/common/api/use-write";
import { COMMON_ISO, COUNTRIES, countryByIso } from "@/common/countries";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ToneChip } from "@/common/ui/status-chip";

import { ConsentCard } from "./consent";
import { browserZone, guessCountry, zoneOptions } from "./places";
import { STEP_LABELS, stepsFor, type Step } from "./steps";

// WEB-CLIENT-001 and WEB-CONTRACTOR-002 at /welcome: consent first, then the role's steps, starting at the
// first one still missing. Only what the backend stores is asked: the client's name, country and time zone;
// the contractor's name and payout account. Not stored, so not shown (PACKAGE-REPORT W-27): the client's
// email if they signed up by phone, the payment currency (chosen per project), notification order; the
// contractor's title, business name and email.

export type OnboardingMe = {
  role: "client" | "contractor";
  full_name: string | null;
  phone: string | null;
  email: string | null;
  country: string | null;
  timezone: string;
};

const fieldClass =
  "min-h-12 w-full rounded-control border border-line-strong bg-white px-3.5 type-body-lg text-ink placeholder:text-muted";

function Progress({ steps, at }: { steps: Exclude<Step, "consent">[]; at: number }) {
  return (
    // Every role has two steps after consent (stepsFor).
    <ol aria-label="Steps" className="grid grid-cols-2 gap-2">
      {steps.map((s, i) => (
        <li key={s} aria-current={i === at ? "step" : undefined} className="flex flex-col gap-2">
          <span aria-hidden className={cn("h-1 rounded-pill", i <= at ? "bg-navy-900" : "bg-line-strong")} />
          <span className={cn("type-small", i === at ? "font-semibold text-ink" : "text-slate")}>
            {i + 1} · {STEP_LABELS[s]}
            {i < at ? <span className="sr-only"> (done)</span> : null}
          </span>
        </li>
      ))}
    </ol>
  );
}

function Panel({ children, actions }: { children: ReactNode; actions: ReactNode }) {
  return (
    <>
      <div className="flex flex-col gap-5 rounded-card border border-line bg-white p-6 shadow-card sm:p-8">
        {children}
      </div>
      <div className="flex flex-wrap items-center justify-between gap-3">{actions}</div>
    </>
  );
}

function Verified({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-1.5">
      <p className="type-small font-semibold text-ink">{label}</p>
      <p className="flex min-h-12 items-center justify-between gap-3 rounded-control border border-line bg-mist px-3.5 text-ink">
        <span className="ibh-tabular">{value}</span>
        <span className="type-small flex items-center gap-1 font-semibold text-ok-fg">
          <Check aria-hidden strokeWidth={2} className="size-4" />
          Verified
        </span>
      </p>
    </div>
  );
}

function SaveProblem({ error }: { error: unknown }) {
  if (!error) return null;
  const state = toUiState(error);
  return (
    <Alert tone="bad" title="That didn’t save">
      {state.kind === "validation"
        ? "Check what you entered and try again."
        : "Nothing was changed. Try again."}
    </Alert>
  );
}

function usePatchMe(onSaved: () => void) {
  return useWrite(
    (body: { full_name?: string; country?: string; timezone?: string }, key: string) =>
      call(api().PATCH("/api/v1/me", { body, headers: { "Idempotency-Key": key } })),
    { onSuccess: onSaved },
  );
}

function DetailsStep({
  me,
  onBack,
  onNext,
}: {
  me: OnboardingMe;
  onBack: (() => void) | null;
  onNext: () => void;
}) {
  const id = useId();
  const [name, setName] = useState(me.full_name ?? "");
  const [problem, setProblem] = useState<string | null>(null);
  const save = usePatchMe(onNext);
  const client = me.role === "client";
  return (
    <form
      noValidate
      className="contents"
      onSubmit={(e) => {
        e.preventDefault();
        if (!name.trim()) {
          setProblem("Enter your full name.");
          return;
        }
        setProblem(null);
        save.mutate({ full_name: name.trim() });
      }}
    >
      <Panel
        actions={
          <>
            {onBack ? (
              <Button type="button" variant="outline" size="lg" onClick={onBack}>
                Back
              </Button>
            ) : (
              <span />
            )}
            <Button type="submit" size="lg" loading={save.isPending}>
              Continue
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-2">
          <h1 className="type-h1 text-ink">{client ? "Tell us about you" : "Your details"}</h1>
          <p className="text-slate">
            {client
              ? "So your contractor and supervisor know who they’re working with."
              : "Shown to your client, the supervisor and our team."}
          </p>
        </div>
        <SaveProblem error={save.error} />
        <div className="flex flex-col gap-1.5">
          <label htmlFor={id} className="type-small font-semibold text-ink">
            Full name
          </label>
          <input
            id={id}
            autoComplete="name"
            value={name}
            maxLength={120}
            onChange={(e) => setName(e.target.value)}
            aria-invalid={problem ? true : undefined}
            aria-describedby={`${id}-help`}
            className={cn(fieldClass, problem && "border-bad-fg")}
          />
          <p id={`${id}-help`} className={cn("type-small", problem ? "text-bad-fg" : "text-muted")}>
            {problem ??
              (client
                ? "Your contractor and supervisor will see this name."
                : "Your client and the supervisor will see this name.")}
          </p>
        </div>
        {me.email ? <Verified label="Email" value={me.email} /> : null}
        {me.phone ? <Verified label="Phone" value={me.phone} /> : null}
      </Panel>
    </form>
  );
}

function LocationStep({ me, onBack, onNext }: { me: OnboardingMe; onBack: () => void; onNext: () => void }) {
  const ids = { country: useId(), zone: useId() };
  const zones = useMemo(() => zoneOptions(), []);
  const [country, setCountry] = useState(
    () =>
      me.country ??
      guessCountry(me.phone, typeof navigator === "undefined" ? undefined : navigator.language) ??
      "",
  );
  const [zone, setZone] = useState(() => (me.timezone !== "UTC" ? me.timezone : (browserZone() ?? "UTC")));
  const save = usePatchMe(onNext);
  const common = COMMON_ISO.map((iso) => countryByIso(iso)!);
  return (
    <form
      noValidate
      className="contents"
      onSubmit={(e) => {
        e.preventDefault();
        if (country) save.mutate({ country, timezone: zone });
      }}
    >
      <Panel
        actions={
          <>
            <Button type="button" variant="outline" size="lg" onClick={onBack}>
              Back
            </Button>
            <Button type="submit" size="lg" loading={save.isPending} disabled={!country}>
              Finish
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-2">
          <h1 className="type-h1 text-ink">Where you are</h1>
          <p className="text-slate">We use this to show every time in your own time zone.</p>
        </div>
        <SaveProblem error={save.error} />
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.country} className="type-small font-semibold text-ink">
            Country you live in
          </label>
          <select
            id={ids.country}
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            className={fieldClass}
          >
            <option value="" disabled>
              Choose your country
            </option>
            <optgroup label="Common">
              {common.map((c) => (
                <option key={`common-${c.iso}`} value={c.iso}>
                  {c.name}
                </option>
              ))}
            </optgroup>
            <optgroup label="All countries">
              {COUNTRIES.map((c) => (
                <option key={c.iso} value={c.iso}>
                  {c.name}
                </option>
              ))}
            </optgroup>
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.zone} className="type-small font-semibold text-ink">
            Time zone
          </label>
          <select
            id={ids.zone}
            value={zone}
            onChange={(e) => setZone(e.target.value)}
            aria-describedby={`${ids.zone}-help`}
            className={fieldClass}
          >
            {zones.map((z) => (
              <option key={z.value} value={z.value}>
                {z.label}
              </option>
            ))}
          </select>
          <p id={`${ids.zone}-help`} className="type-small text-muted">
            Detected from your browser. Every time in iBackHome is shown in this zone.
          </p>
        </div>
      </Panel>
    </form>
  );
}

type Recipient = { bank_name: string; account_name: string; account_number_masked: string };

function PayoutStep({ onBack, onNext }: { onBack: () => void; onNext: () => void }) {
  const ids = { bank: useId(), number: useId() };
  const [bank, setBank] = useState("");
  const [number, setNumber] = useState("");
  const [saved, setSaved] = useState<Recipient | null>(null);
  const [changing, setChanging] = useState(false);
  const banks = useQuery({
    queryKey: ["banks"],
    queryFn: () => call(api().GET("/api/v1/banks")),
    staleTime: 60 * 60_000,
  });
  const ready = Boolean(bank) && /^\d{10}$/.test(number);
  const lookup = useQuery({
    queryKey: ["account-name", bank, number],
    enabled: ready,
    retry: false,
    queryFn: () =>
      call(
        api().POST("/api/v1/me/payout/recipient/resolve", {
          body: { bank_code: bank, account_number: number },
        }),
      ),
  });
  const save = useWrite(
    (body: { bank_code: string; account_number: string }, key: string) =>
      call(api().PUT("/api/v1/me/payout/recipient", { body, headers: { "Idempotency-Key": key } })),
    {
      onSuccess: (recipient) => {
        setSaved(recipient);
        setChanging(false);
        setNumber("");
      },
    },
  );
  const unavailable = [banks.error, lookup.error, save.error].some(
    (e) =>
      e instanceof ApiError && (e.code === "paystack_not_configured" || e.code === "paystack_unavailable"),
  );

  if (saved && !changing) {
    return (
      <Panel
        actions={
          <>
            <Button type="button" variant="outline" size="lg" onClick={onBack}>
              Back
            </Button>
            <Button type="button" size="lg" onClick={onNext}>
              Go to my projects
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-2">
          <h1 className="type-h1 text-ink">Payout account saved</h1>
          <p className="text-slate">After saving we keep only the last four digits of the account number.</p>
        </div>
        <div className="flex flex-wrap items-center gap-4 rounded-card border border-line p-4">
          <span className="flex size-11 flex-none items-center justify-center rounded-control bg-mist text-ink">
            <Landmark aria-hidden strokeWidth={1.75} className="size-5" />
          </span>
          <div className="flex flex-1 flex-col">
            <p className="font-semibold text-ink">{saved.bank_name}</p>
            <p className="type-mono text-slate">
              {saved.account_number_masked} · {saved.account_name}
            </p>
          </div>
          <ToneChip label="Ready for payouts" tone="ok" size="small" />
        </div>
        <p className="type-small flex items-start gap-2 rounded-control bg-mist p-3 text-slate">
          <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
          Payments come from the licensed escrow partner, in naira, after each milestone is verified and
          approved.
        </p>
        <button
          type="button"
          onClick={() => setChanging(true)}
          className="self-start rounded-control font-semibold text-accent underline"
        >
          Change account
        </button>
      </Panel>
    );
  }

  return (
    <form
      noValidate
      className="contents"
      onSubmit={(e) => {
        e.preventDefault();
        if (ready && lookup.data) save.mutate({ bank_code: bank, account_number: number });
      }}
    >
      <Panel
        actions={
          <>
            <Button
              type="button"
              variant="outline"
              size="lg"
              onClick={saved ? () => setChanging(false) : onBack}
            >
              Back
            </Button>
            <Button type="submit" size="lg" loading={save.isPending} disabled={!lookup.data}>
              Save payout account
            </Button>
          </>
        }
      >
        <div className="flex flex-col gap-2">
          <h1 className="type-h1 text-ink">Where should we pay you?</h1>
          <p className="text-slate">A Nigerian bank account in your name or your business’s name.</p>
        </div>
        {unavailable ? (
          <Alert tone="warn" title="Bank details can’t be checked right now">
            Try again in a few minutes. Your other details are saved.
          </Alert>
        ) : save.error ? (
          <Alert tone="bad" title="That account wasn’t saved">
            Check the bank and number, then try again.
          </Alert>
        ) : null}
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.bank} className="type-small font-semibold text-ink">
            Bank
          </label>
          <select
            id={ids.bank}
            value={bank}
            onChange={(e) => setBank(e.target.value)}
            disabled={!banks.data}
            className={fieldClass}
          >
            <option value="" disabled>
              {banks.isPending ? "Loading banks…" : "Choose your bank"}
            </option>
            {(banks.data ?? []).map((b) => (
              <option key={b.code} value={b.code}>
                {b.name}
              </option>
            ))}
          </select>
        </div>
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.number} className="type-small font-semibold text-ink">
            Account number (NUBAN, 10 digits)
          </label>
          <input
            id={ids.number}
            inputMode="numeric"
            autoComplete="off"
            maxLength={10}
            value={number}
            onChange={(e) => setNumber(e.target.value.replace(/\D/g, ""))}
            aria-describedby={`${ids.number}-status`}
            className={cn(fieldClass, "ibh-tabular")}
          />
        </div>
        <div id={`${ids.number}-status`} aria-live="polite">
          {lookup.data ? (
            <div className="flex items-center gap-3 rounded-control bg-ok-bg p-4">
              <CircleCheck aria-hidden strokeWidth={1.75} className="size-5 text-ok-fg" />
              <div>
                <p className="type-small font-semibold text-ok-fg">Account found</p>
                <p className="font-semibold text-ink">{lookup.data.account_name}</p>
              </div>
            </div>
          ) : lookup.isFetching ? (
            <p className="type-small text-slate">Checking the account…</p>
          ) : lookup.error && !unavailable ? (
            <Alert tone="bad" title="We couldn’t find that account">
              Check the number and the bank.
            </Alert>
          ) : null}
        </div>
        <p className="type-small text-slate">
          Is this you? The name must match your profile or registered business. After saving we keep only the
          last four digits.
        </p>
      </Panel>
    </form>
  );
}

export function Onboarding({ me, missing, home }: { me: OnboardingMe; missing: Step[]; home: string }) {
  const steps = stepsFor(me.role) as Exclude<Step, "consent">[];
  const first = Math.max(
    0,
    steps.findIndex((s) => missing.includes(s)),
  );
  const [consented, setConsented] = useState(!missing.includes("consent"));
  const [at, setAt] = useState(first);
  const finish = () => window.location.assign(home);
  const next = () => (at + 1 < steps.length ? setAt(at + 1) : finish());
  const back = at > 0 ? () => setAt(at - 1) : null;

  if (!consented)
    return (
      <div className="mx-auto w-full max-w-lg rounded-card border border-line bg-white p-6 shadow-card sm:p-8">
        <ConsentCard
          onDone={() => {
            setConsented(true);
            // Already-complete steps aren't asked again.
            if (!missing.some((s) => s !== "consent")) finish();
          }}
        />
      </div>
    );

  const step = steps[at]!;
  return (
    <div className="mx-auto flex w-full max-w-2xl flex-col gap-6">
      <Progress steps={steps} at={at} />
      {step === "details" ? (
        <DetailsStep me={me} onBack={back} onNext={next} />
      ) : step === "location" ? (
        <LocationStep me={me} onBack={() => setAt(at - 1)} onNext={next} />
      ) : (
        <PayoutStep onBack={() => setAt(at - 1)} onNext={next} />
      )}
    </div>
  );
}
