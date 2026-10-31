"use client";

import { useRouter } from "next/navigation";
import { useId, useMemo, useState } from "react";

import { api, call } from "@/common/api/client";
import type { components } from "@/common/api/schema";
import { useWrite } from "@/common/api/use-write";
import { COUNTRIES, COMMON_ISO, countryByIso } from "@/common/countries";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { SelectField, TextField } from "@/common/ui/field";
import { zoneOptions } from "@/features/auth/onboarding/places";

// The signed-in person's editable details: name, country and time zone (PATCH /me). Phone and email are how
// they sign in, so they are shown but not changed here.

export type Me = components["schemas"]["MeOut"];

export function ProfileForm({ me, onDone }: { me: Me; onDone?: () => void }) {
  const router = useRouter();
  const ids = { name: useId(), country: useId(), zone: useId() };
  const zones = useMemo(() => zoneOptions(), []);
  const [name, setName] = useState(me.full_name ?? "");
  const [country, setCountry] = useState(me.country ?? "");
  const [zone, setZone] = useState(me.timezone);
  const [problem, setProblem] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const common = COMMON_ISO.map((iso) => countryByIso(iso)!);

  const save = useWrite(
    (body: { full_name: string; country?: string; timezone: string }, key: string) =>
      call(api().PATCH("/api/v1/me", { body, headers: { "Idempotency-Key": key } })),
    {
      onSuccess: () => {
        setSaved(true);
        router.refresh(); // the top bar shows the name from the server
        onDone?.();
      },
    },
  );

  return (
    <form
      noValidate
      className="flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        setSaved(false);
        if (!name.trim()) return setProblem("Enter your full name.");
        setProblem(null);
        save.mutate({ full_name: name.trim(), ...(country ? { country } : {}), timezone: zone });
      }}
    >
      {save.error ? (
        <Alert tone="bad" title="That didn’t save">
          Nothing was changed. Try again.
        </Alert>
      ) : null}
      {saved && !onDone ? (
        <Alert tone="ok" title="Saved">
          Your details are updated.
        </Alert>
      ) : null}
      <TextField
        id={ids.name}
        label="Full name"
        autoComplete="name"
        value={name}
        maxLength={120}
        onChange={(e) => setName(e.target.value)}
        error={problem}
        help="Your client, the supervisor and our team see this name."
      />
      <SelectField
        id={ids.country}
        label="Country"
        value={country}
        onChange={(e) => setCountry(e.target.value)}
        help="Where you live now."
      >
        <option value="">Not set</option>
        <optgroup label="Common">
          {common.map((c) => (
            <option key={c.iso} value={c.iso}>
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
      </SelectField>
      <SelectField
        id={ids.zone}
        label="Time zone"
        value={zone}
        onChange={(e) => setZone(e.target.value)}
        help="Dates and times across iBackHome are shown in this zone."
      >
        {zones.some((z) => z.value === zone) ? null : <option value={zone}>{zone}</option>}
        {zones.map((z) => (
          <option key={z.value} value={z.value}>
            {z.label}
          </option>
        ))}
      </SelectField>
      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={save.isPending}>
          Save
        </Button>
        {onDone ? (
          <Button type="button" variant="secondary" onClick={onDone}>
            Cancel
          </Button>
        ) : null}
      </div>
    </form>
  );
}
