"use client";

import { useQuery } from "@tanstack/react-query";

import { api, call } from "@/common/api/client";
import { countryByIso } from "@/common/countries";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { Avatar, Card, CardLabel } from "@/common/ui/surfaces";

import { ProfileForm } from "./profile-form";

// Your profile, for every role: what we hold about you (GET /me) and the fields you can change (PATCH /me).

const ROLE: Record<string, string> = {
  client: "Client",
  contractor: "Contractor",
  supervisor: "Supervisor",
  supplier: "Supplier",
  ops: "Operations",
};

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4">
      <dt className="text-slate">{label}</dt>
      <dd className="min-w-0 text-right font-semibold break-words text-ink">{value}</dd>
    </div>
  );
}

export function ProfilePage() {
  const me = useQuery({ queryKey: ["me"], queryFn: () => call(api().GET("/api/v1/me")) });
  if (me.isPending) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-10">
        <Loading label="Loading your profile">
          <Skeleton className="h-36 w-full" />
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  }
  if (me.error || !me.data) return <ServerErrorContent reference={null} onRetry={() => void me.refetch()} />;
  const person = me.data;
  return (
    <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-10">
      <h1 className="sr-only">Your profile</h1>
      <Card className="flex items-center gap-5 p-6">
        <Avatar name={person.full_name} size={40} />
        <div className="flex min-w-0 flex-col gap-1">
          <p className="type-h1 text-ink">{person.full_name ?? "Add your name"}</p>
          <p className="text-slate">{ROLE[person.role] ?? person.role}</p>
        </div>
      </Card>
      <Card className="flex flex-col gap-4 p-6">
        <h2 className="type-h3 text-ink">Your details</h2>
        <ProfileForm key={`${person.full_name}|${person.country}|${person.timezone}`} me={person} />
      </Card>
      <Card className="flex flex-col gap-3 p-5">
        <CardLabel>Sign-in and account</CardLabel>
        <dl className="flex flex-col gap-2">
          {person.phone ? <Row label="Phone" value={person.phone} /> : null}
          {person.email ? <Row label="Email" value={person.email} /> : null}
          <Row label="Role" value={ROLE[person.role] ?? person.role} />
          <Row label="Account status" value={person.status === "active" ? "Active" : "Suspended"} />
          {person.country ? (
            <Row label="Country" value={countryByIso(person.country)?.name ?? person.country} />
          ) : null}
        </dl>
        <p className="type-small text-slate">
          Your phone number or email is how you sign in, so it can’t be changed here.
        </p>
      </Card>
    </div>
  );
}
