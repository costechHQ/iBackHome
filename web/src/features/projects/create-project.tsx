"use client";

import { Lock } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import { toUiState } from "@/common/api/errors";
import { ApiError } from "@/common/api/errors";
import { countryByIso } from "@/common/countries";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { Card } from "@/common/ui/surfaces";
import { CountryPicker } from "@/features/auth/country-picker";
import { phoneIdentifier } from "@/features/auth/otp";

import { useCreateProject } from "./api";

// WEB-CLIENT-003 CS-02/03 "New project". The backend keeps BoQ lines and milestones in the project's currency
// and pays in naira, so a project is created in NGN and the budget is entered in naira (PACKAGE-REPORT B-6).
// The contractor is invited by phone (POST /projects contractor_phone); an email invite, the contractor's
// name and the area list aren't stored, so the address takes the street and area as typed (W-31).

const field =
  "min-h-12 w-full rounded-control border bg-white px-3.5 type-body-lg text-ink placeholder:text-muted";

type Problems = Partial<Record<"title" | "street" | "area" | "budget" | "phone", string>>;

/** Naira typed with commas ("25,000,000") to kobo; null if it isn't a positive whole number of naira. */
export function nairaToKobo(typed: string): number | null {
  const digits = typed.replace(/[,\s₦]/g, "");
  if (!/^\d{1,12}$/.test(digits)) return null;
  const naira = Number(digits);
  return naira > 0 ? naira * 100 : null;
}

/** The design's message for a Nigerian number of the wrong length; null when the length is right. */
export function nigerianLengthProblem(typed: string): string | null {
  const digits = typed.replace(/\D/g, "").replace(/^0/, "");
  if (digits.length === 10) return null;
  const off = 10 - digits.length;
  const word = Math.abs(off) === 1 ? "digit" : "digits";
  return `That number is ${Math.abs(off)} ${word} ${off > 0 ? "short" : "too long"}. Nigerian mobiles have 10 digits after +234.`;
}

export function CreateProject() {
  const router = useRouter();
  const ids = { title: useId(), street: useId(), area: useId(), budget: useId(), phone: useId() };
  const [title, setTitle] = useState("");
  const [street, setStreet] = useState("");
  const [area, setArea] = useState("");
  const [budget, setBudget] = useState("");
  const [iso, setIso] = useState("NG");
  const [phone, setPhone] = useState("");
  const [problems, setProblems] = useState<Problems>({});
  const create = useCreateProject();

  const submit = () => {
    const next: Problems = {};
    if (!title.trim()) next.title = "Give the project a name.";
    if (!street.trim()) next.street = "Enter the site address.";
    if (!area.trim()) next.area = "Enter the area.";
    const kobo = nairaToKobo(budget);
    if (kobo === null) next.budget = "Enter the budget in naira, for example 25,000,000.";
    if (!phone.trim()) next.phone = "Enter your contractor's phone number.";
    else if (iso === "NG" && !phone.trim().startsWith("+")) {
      const length = nigerianLengthProblem(phone);
      if (length) next.phone = length;
    }
    setProblems(next);
    if (Object.keys(next).length || kobo === null) return;
    create.mutate(
      {
        title: title.trim(),
        address: `${street.trim()}, ${area.trim()}, Enugu`,
        currency: "NGN",
        budget_minor: kobo,
        contractor_phone: phoneIdentifier(countryByIso(iso)?.dial ?? "234", phone),
      },
      { onSuccess: (project) => router.push(`/projects/${project.id}/setup`) },
    );
  };

  const serverProblem = (() => {
    if (!create.error) return null;
    if (create.error instanceof ApiError && create.error.code === "role_conflict")
      return "That phone number belongs to someone who isn't a contractor on iBackHome. Check the number.";
    if (create.error instanceof ApiError && create.error.code === "invalid_phone")
      return "That isn't a phone number we can send to. Check the number and the country code.";
    return toUiState(create.error).kind === "offline"
      ? "You're offline. Nothing was created."
      : "We couldn't create the project. Nothing was saved. Try again.";
  })();

  const error = (key: keyof Problems, id: string) =>
    problems[key] ? (
      <p id={`${id}-error`} className="type-small text-bad-fg">
        {problems[key]}
      </p>
    ) : null;
  const described = (key: keyof Problems, id: string) => (problems[key] ? `${id}-error` : undefined);

  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 sm:px-12 lg:grid-cols-3">
      <Card className="flex flex-col gap-5 p-6 sm:p-8 lg:col-span-2">
        <h1 className="type-h1 text-ink">New project</h1>
        {serverProblem ? <Alert tone="bad" title={serverProblem} /> : null}
        <form
          noValidate
          className="flex flex-col gap-5"
          onSubmit={(e) => {
            e.preventDefault();
            submit();
          }}
        >
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.title} className="type-small font-semibold text-ink">
              Project name
            </label>
            <input
              id={ids.title}
              value={title}
              maxLength={200}
              onChange={(e) => setTitle(e.target.value)}
              aria-invalid={problems.title ? true : undefined}
              aria-describedby={described("title", ids.title)}
              className={cn(field, problems.title ? "border-bad-fg" : "border-line-strong")}
            />
            {error("title", ids.title)}
          </div>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex flex-col gap-1.5 sm:col-span-2">
              <label htmlFor={ids.street} className="type-small font-semibold text-ink">
                Site address
              </label>
              <input
                id={ids.street}
                value={street}
                autoComplete="street-address"
                onChange={(e) => setStreet(e.target.value)}
                aria-invalid={problems.street ? true : undefined}
                aria-describedby={described("street", ids.street)}
                className={cn(field, problems.street ? "border-bad-fg" : "border-line-strong")}
              />
              {error("street", ids.street)}
            </div>
            <div className="flex flex-col gap-1.5">
              <label htmlFor={ids.area} className="type-small font-semibold text-ink">
                Area, Enugu
              </label>
              <input
                id={ids.area}
                value={area}
                onChange={(e) => setArea(e.target.value)}
                aria-invalid={problems.area ? true : undefined}
                aria-describedby={described("area", ids.area)}
                className={cn(field, problems.area ? "border-bad-fg" : "border-line-strong")}
              />
              {error("area", ids.area)}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <label htmlFor={ids.budget} className="type-small font-semibold text-ink">
              Total budget (naira)
            </label>
            <div className="relative">
              <span
                aria-hidden
                className="pointer-events-none absolute top-1/2 left-3.5 -translate-y-1/2 text-slate"
              >
                ₦
              </span>
              <input
                id={ids.budget}
                inputMode="numeric"
                value={budget}
                onChange={(e) => setBudget(e.target.value)}
                aria-invalid={problems.budget ? true : undefined}
                aria-describedby={`${ids.budget}-help`}
                className={cn(
                  field,
                  "ibh-tabular pl-8",
                  problems.budget ? "border-bad-fg" : "border-line-strong",
                )}
              />
            </div>
            <p
              id={`${ids.budget}-help`}
              className={cn("type-small", problems.budget ? "text-bad-fg" : "text-muted")}
            >
              {problems.budget ??
                "For your reference. Your contractor prices the work in naira, and the BoQ can be above it — we'll show both. You pay each milestone in your own currency."}
            </p>
          </div>
          <div className="flex flex-col gap-1.5 border-t border-line pt-5">
            <label
              id={`${ids.phone}-label`}
              htmlFor={ids.phone}
              className="type-small font-semibold text-ink"
            >
              Contractor&apos;s phone
            </label>
            <div className="flex gap-2">
              <CountryPicker value={iso} onChange={setIso} labelId={`${ids.phone}-label`} />
              <input
                id={ids.phone}
                type="tel"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                aria-invalid={problems.phone ? true : undefined}
                aria-describedby={described("phone", ids.phone)}
                className={cn(field, problems.phone ? "border-bad-fg" : "border-line-strong")}
              />
            </div>
            {error("phone", ids.phone)}
          </div>
          <div className="flex flex-wrap justify-end gap-3">
            <Button asChild variant="outline" size="lg">
              <Link href="/projects">Cancel</Link>
            </Button>
            <Button type="submit" size="lg" loading={create.isPending}>
              Create and invite
            </Button>
          </div>
        </form>
      </Card>
      <aside className="flex flex-col gap-4">
        <Card className="flex flex-col gap-3 p-5">
          <h2 className="type-h3 text-ink">After you create it</h2>
          <ol className="flex flex-col gap-3">
            {[
              "Your contractor is added to the project and signs in with their phone",
              "You pin the site and draw its boundary",
              "We assign a vetted supervisor",
              "Your contractor prices the work; you, they and our team approve it",
            ].map((text, i) => (
              <li key={text} className="flex items-start gap-3 text-slate">
                <span className="type-small flex size-6 flex-none items-center justify-center rounded-pill bg-mist font-semibold text-ink">
                  {i + 1}
                </span>
                {text}
              </li>
            ))}
          </ol>
        </Card>
        <Card className="type-small flex items-start gap-3 p-5 text-slate">
          <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
          No money moves until the BoQ is approved and you fund a milestone. Funds are held by a licensed
          escrow partner, never by iBackHome.
        </Card>
      </aside>
    </div>
  );
}
