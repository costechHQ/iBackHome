"use client";

import { useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { useProjectsWithMilestones } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";
import { countryByIso } from "@/common/countries";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { TextField } from "@/common/ui/field";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Avatar, Card, CardLabel } from "@/common/ui/surfaces";

import { usePayoutRecipient } from "./account";
import { trackRecord } from "./track-record";

// WEB-CONTRACTOR-009 Profile at /c/profile: who the contractor is to iBackHome and the facts the platform
// recorded about their work. Only what the backend has (PACKAGE-REPORT W-40): the name (editable, PATCH /me),
// the phone or email they sign in with, the payout account check, project counts and three counts from their
// milestones. Not shown until MX-23: the COREN/CAC check badges, "About the business", "on iBackHome since",
// first-time verification and average days, disputes decided against them, and "Clients can see" (clients
// can't open a contractor's profile yet, MX-26).

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <div className="flex flex-col gap-1 rounded-control bg-mist p-4">
      <p className="ibh-tabular type-h2 text-ink">{value}</p>
      <p className="type-small text-slate">{label}</p>
    </div>
  );
}

function EditName({ name, onDone }: { name: string; onDone: () => void }) {
  const router = useRouter();
  const [value, setValue] = useState(name);
  const [problem, setProblem] = useState<string | null>(null);
  const save = useWrite(
    (body: { full_name: string }, key: string) =>
      call(api().PATCH("/api/v1/me", { body, headers: { "Idempotency-Key": key } })),
    {
      onSuccess: () => {
        router.refresh(); // the top bar shows the name from the server
        onDone();
      },
    },
  );
  return (
    <form
      noValidate
      className="flex flex-col gap-3"
      onSubmit={(e) => {
        e.preventDefault();
        if (!value.trim()) return setProblem("Enter your full name.");
        setProblem(null);
        save.mutate({ full_name: value.trim() });
      }}
    >
      {save.error ? (
        <Alert tone="bad" title="That didn’t save">
          Nothing was changed. Try again.
        </Alert>
      ) : null}
      <TextField
        label="Full name"
        autoComplete="name"
        value={value}
        maxLength={120}
        onChange={(e) => setValue(e.target.value)}
        error={problem}
        help="Your client, the supervisor and our team see this name."
      />
      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={save.isPending}>
          Save
        </Button>
        <Button type="button" variant="secondary" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

export function ContractorProfile() {
  const me = useQuery({ queryKey: ["me"], queryFn: () => call(api().GET("/api/v1/me")) });
  const work = useProjectsWithMilestones();
  const payout = usePayoutRecipient();
  const [editing, setEditing] = useState(false);

  if (me.isPending || work.isPending) {
    return (
      <div className="mx-auto w-full max-w-7xl px-4 py-8 sm:px-10">
        <Loading label="Loading your profile">
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-48 w-full" />
        </Loading>
      </div>
    );
  }
  if (me.error || !me.data) return <ServerErrorContent reference={null} onRetry={() => void me.refetch()} />;
  if (work.error) return <ServerErrorContent reference={null} onRetry={work.refetch} />;

  const person = me.data;
  const record = trackRecord(work.items);
  const country = person.country ? countryByIso(person.country)?.name : null;
  return (
    <div className="mx-auto grid w-full max-w-7xl gap-6 px-4 py-8 sm:px-10 lg:grid-cols-3">
      <div className="flex flex-col gap-6 lg:col-span-2">
        <h1 className="sr-only">Your profile</h1>
        <Card className="flex flex-col gap-4 p-6">
          {editing ? (
            <EditName name={person.full_name ?? ""} onDone={() => setEditing(false)} />
          ) : (
            <div className="flex flex-wrap items-start gap-5">
              <Avatar name={person.full_name} size={40} />
              <div className="flex min-w-0 flex-1 flex-col gap-2">
                <p className="type-h1 text-ink">{person.full_name ?? "Add your name"}</p>
                <p className="text-slate">
                  Contractor{country ? ` · ${country}` : ""}
                  {person.phone ? ` · ${person.phone}` : person.email ? ` · ${person.email}` : ""}
                </p>
                <div className="flex flex-wrap gap-2">
                  {payout.recipient ? (
                    <ToneChip label="Payout account name matched by the bank" tone="ok" size="small" />
                  ) : payout.recipient === null ? (
                    <ToneChip label="No payout account yet" tone="warn" size="small" />
                  ) : null}
                </div>
              </div>
              <Button variant="outline" onClick={() => setEditing(true)}>
                Edit profile
              </Button>
            </div>
          )}
        </Card>

        <Card className="flex flex-col gap-4 p-6">
          <h2 className="type-h3 text-ink">Track record on iBackHome</h2>
          <div className="grid gap-3 sm:grid-cols-3">
            <Stat value={record.verified} label="milestones verified by a supervisor" />
            <Stat value={record.released} label="milestones released" />
            <Stat value={record.sentBackNow} label="claims sent back and waiting for rework" />
          </div>
          <p className="type-small text-slate">
            Worked out from your milestones on iBackHome. You can’t edit these numbers.
          </p>
        </Card>
      </div>

      <aside className="flex flex-col gap-6">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Projects</CardLabel>
          <dl className="flex flex-col gap-2">
            {[
              ["Active", record.projects.active],
              ["In setup", record.projects.settingUp],
              ["Completed on iBackHome", record.projects.completed],
            ].map(([label, n]) => (
              <div key={label} className="flex justify-between gap-3">
                <dt className="text-ink">{label}</dt>
                <dd className="ibh-tabular font-semibold text-ink">{n}</dd>
              </div>
            ))}
          </dl>
        </Card>
        <Card className="flex flex-col gap-2 p-5">
          <CardLabel>Private to you and our team</CardLabel>
          <p className="type-small text-slate">
            Your bank details and your payouts are seen only by you and our team.
          </p>
        </Card>
      </aside>
    </div>
  );
}
