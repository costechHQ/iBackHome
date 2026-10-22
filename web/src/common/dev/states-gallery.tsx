"use client";

import { Inbox } from "lucide-react";
import Link from "next/link";
import { useState, type ReactNode } from "react";

import { Alert } from "../ui/alert";
import { Button } from "../ui/button";
import { ConfirmDialog } from "../ui/dialog";
import { ErrorSummary, SelectField, TextField } from "../ui/field";
import { EscrowTrustLine, MoneyInline, MoneyLarge } from "../ui/money-display";
import { SegmentedControl } from "../ui/segmented";
import { Loading, Skeleton } from "../ui/skeleton";
import { StatusChip, ToneChip } from "../ui/status-chip";
import { Card, CardLabel, EmptyState } from "../ui/surfaces";
import { Table, Td, Th, Tr } from "../ui/table";
import { Time } from "../ui/time";
import { useToast } from "../ui/toast";
import { ClientNav, ClientTop, ProjectHeader } from "../layout/client-shell";
import { ContractorTop } from "../layout/contractor-shell";
import { ForbiddenPage } from "../layout/forbidden-page";
import { OfflineBar, useOnline } from "../layout/online";
import { OpsHeader, OpsSidebar } from "../layout/ops-shell";
import { ConflictState, NotFoundContent, ServerErrorContent } from "../layout/system-pages";

// DEV ONLY (/dev/states, 404 unless IBH_DEV_PAGES=1): every shared state and shell, one frame per ?frame=,
// for the axe checks and the screenshot comparison with the WEB-CLIENT-024 PNGs. Sample text is neutral on
// purpose: no names, amounts or IDs from the design fixtures.

const NAME = "Sample Client";
const PROJECTS = [
  { id: "p1", title: "Sample bungalow" },
  { id: "p2", title: "Second project" },
];

function ClientFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <ClientTop name={NAME} projects={PROJECTS} />
      <main className="flex flex-1 flex-col bg-mist">{children}</main>
    </div>
  );
}

function Backdrop() {
  return (
    <div className="flex flex-col gap-6 p-10">
      <Skeleton className="h-7 w-88" />
      <Skeleton className="h-40 w-full" />
    </div>
  );
}

function LiveOffline() {
  const online = useOnline();
  return (
    <div className="flex min-h-dvh flex-col">
      <OfflineBar />
      <main className="flex flex-col gap-4 p-10">
        <Button size="lg" disabled={!online}>
          Review and approve
        </Button>
      </main>
    </div>
  );
}

function Toasts() {
  const toast = useToast();
  return (
    <div className="p-10">
      <Button
        onClick={() => {
          toast({ message: "Sample order approved. The supplier will deliver." });
          toast({ message: "Notification settings saved." });
          toast({ message: "Receipt downloaded.", action: { label: "Open", onClick: () => {} } });
        }}
      >
        Show toasts
      </Button>
    </div>
  );
}

function Kit() {
  const [tab, setTab] = useState<"open" | "resolved">("open");
  return (
    <div className="flex flex-col gap-8 bg-canvas p-8">
      <section className="flex flex-wrap items-center gap-3">
        <Button>Primary</Button>
        <Button loading>Saving</Button>
        <Button disabled>Disabled</Button>
        <Button variant="secondary">Secondary</Button>
        <Button variant="outline">Outline</Button>
        <Button variant="text">Text link</Button>
        <div className="flex gap-3 rounded-card bg-navy-900 p-3">
          <Button variant="white-on-navy">Approve release</Button>
          <Button variant="outline-on-navy">Raise a dispute</Button>
        </div>
      </section>
      <section className="flex flex-wrap gap-2">
        {["pending", "funded", "claimed", "verified", "approved", "disputed", "released"].map((s) => (
          <StatusChip key={s} entity="milestone" state={s} audience="client" />
        ))}
        <StatusChip entity="evidence" state="flagged" audience="client" />
        <StatusChip entity="evidence" state="flagged" audience="ops" />
        <ToneChip label="Waiting for 2nd approver" tone="warn" size="small" />
      </section>
      <section className="grid gap-3 md:grid-cols-2">
        <Alert tone="info" title="Sample milestone is waiting for your approval">
          The supervisor verified it. Approve to release.
        </Alert>
        <Alert tone="ok" title="Release confirmed" />
        <Alert tone="warn" title="Taking longer than usual">
          We&apos;ll message you when it&apos;s done.
        </Alert>
        <Alert tone="bad" title="We couldn't send your code by SMS.">
          Try again, or choose another way to get it.
        </Alert>
      </section>
      <section className="grid gap-4 md:grid-cols-2">
        <Card className="flex flex-col gap-3 p-5">
          <CardLabel>Money</CardLabel>
          <MoneyInline
            ngnMinor={1_326_000_000}
            client={{ amountMinor: 680_000, currency: "GBP" }}
            rate={{ fxRate: "1950.0000000000", on: "Mon 30 Nov" }}
          />
          <MoneyInline
            ngnMinor={1_482_000_000}
            client={{ amountMinor: 760_000, currency: "GBP", estimate: true }}
          />
          <MoneyInline ngnMinor={760_500_000} />
          <EscrowTrustLine variant="card" />
        </Card>
        <Card className="flex flex-col items-end gap-3 p-5">
          <MoneyLarge
            ngnMinor={1_326_000_000}
            client={{ amountMinor: 680_000, currency: "GBP" }}
            rate={{ fxRate: "1950.0000000000", on: "Funded Mon 30 Nov" }}
          />
          <p className="type-small">
            Released <Time iso="2026-12-12T09:26:00Z" timeZone="Europe/London" />
          </p>
        </Card>
      </section>
      <section className="flex flex-col gap-3">
        <SegmentedControl
          label="Dispute status"
          value={tab}
          onChange={setTab}
          segments={[
            { value: "open", label: "Open", count: 2 },
            { value: "resolved", label: "Resolved", count: 14 },
          ]}
        />
        <Table caption="Sample table" dense>
          <thead>
            <tr>
              <Th>Dispute</Th>
              <Th>Project · milestone</Th>
              <Th numeric>Held</Th>
              <Th>Status</Th>
            </tr>
          </thead>
          <tbody>
            <Tr>
              <Td className="type-mono">D-0001</Td>
              <Td>Sample bungalow · Roofing</Td>
              <Td numeric>₦9,120,000</Td>
              <Td>
                <ToneChip label="Waiting for 2nd approver" tone="warn" size="small" />
              </Td>
            </Tr>
          </tbody>
        </Table>
      </section>
      <Card>
        <EmptyState
          icon={Inbox}
          title="No disputes right now"
          action={<Button variant="secondary">Refresh</Button>}
        >
          New disputes appear here as soon as a client raises one.
        </EmptyState>
      </Card>
    </div>
  );
}

/** Frames built from a feature (common/ can't import features/): the gallery page passes them in. */
export type GallerySlots = { sessionExpired: ReactNode };

const FRAMES: Record<string, { label: string; render: (slots: GallerySlots) => ReactNode }> = {
  "404": {
    label: "404 · page not found",
    render: () => (
      <ClientFrame>
        <NotFoundContent />
      </ClientFrame>
    ),
  },
  "500": {
    label: "500 · server error",
    render: () => (
      <ClientFrame>
        <ServerErrorContent reference="ERR-SAMPLE" onRetry={() => {}} />
      </ClientFrame>
    ),
  },
  "403": {
    label: "Permission denied · 403",
    render: () => (
      <ForbiddenPage
        portal="client"
        me={{ full_name: "Sample Contractor", role: "contractor", status: "active" }}
      />
    ),
  },
  "409": {
    label: "409 · conflict",
    render: () => (
      <ClientFrame>
        <ConflictState
          title="Roofing was already approved"
          code="Error 409 · same request recognised"
          actions={
            <>
              <Button size="lg">See release status</Button>
              <Button size="lg" variant="outline">
                Back to project
              </Button>
            </>
          }
        >
          <p>You approved it on another device, so nothing was sent twice. The release is in progress.</p>
        </ConflictState>
      </ClientFrame>
    ),
  },
  form: {
    label: "Form validation",
    render: () => (
      <ClientFrame>
        <div className="flex max-w-xl flex-col gap-5 p-10">
          <h1 className="type-h2 text-ink">Your details</h1>
          <ErrorSummary
            problems={[
              { fieldId: "wa", message: "WhatsApp number is missing a country code" },
              { fieldId: "cur", message: "Choose the currency you'll pay in" },
            ]}
          />
          <TextField
            id="wa"
            label="WhatsApp number"
            defaultValue="07700 900000"
            error="Add your country code, for example +44 7700 900000."
          />
          <SelectField id="cur" label="Currency you'll pay in" error="Choose one." defaultValue="">
            <option value="" disabled>
              Choose
            </option>
            <option>GBP £</option>
            <option>USD $</option>
            <option>EUR €</option>
          </SelectField>
          <Button size="lg" block>
            Continue
          </Button>
        </div>
      </ClientFrame>
    ),
  },
  session: {
    label: "Session expired",
    render: (slots) => (
      <ClientFrame>
        <Backdrop />
        {slots.sessionExpired}
      </ClientFrame>
    ),
  },
  offline: {
    label: "Offline",
    render: () => (
      <div className="flex min-h-dvh flex-col">
        <OfflineBar force />
        <ClientTop name={NAME} projects={PROJECTS} />
        <main className="flex flex-col gap-4 bg-mist p-10">
          <Card className="flex items-center justify-between gap-6 p-5">
            <div>
              <p className="font-semibold text-ink">Roofing is verified · approve to release</p>
              <MoneyInline
                className="type-small"
                ngnMinor={1_326_000_000}
                client={{ amountMinor: 680_000, currency: "GBP" }}
                rate={{ fxRate: "1950.00" }}
              />
            </div>
            <Button size="lg" disabled>
              Review and approve
            </Button>
          </Card>
          <p className="type-small text-muted">
            The button comes back when you&apos;re online. Nothing is queued or sent automatically on the web.
          </p>
        </main>
      </div>
    ),
  },
  "offline-live": {
    label: "Offline bar, following the real connection",
    render: () => <LiveOffline />,
  },
  loading: {
    label: "Loading skeleton",
    render: () => (
      <ClientFrame>
        <div className="p-10">
          <Loading label="Loading the project">
            <Skeleton className="h-7 w-88" />
            <Skeleton className="h-40 w-full" />
          </Loading>
        </div>
      </ClientFrame>
    ),
  },
  toasts: {
    label: "Success toasts",
    render: () => (
      <ClientFrame>
        <Toasts />
      </ClientFrame>
    ),
  },
  confirm: {
    label: "Confirmation dialog",
    render: () => (
      <ClientFrame>
        <Backdrop />
        <ConfirmDialog
          open
          onOpenChange={() => {}}
          title="Approve this order?"
          confirmLabel="Approve order"
          onConfirm={() => {}}
          aboutMoney
          description={
            <>
              It&apos;s paid from the milestone&apos;s escrow after the supervisor confirms delivery. Held by
              a licensed escrow partner, never by iBackHome.
            </>
          }
        />
      </ClientFrame>
    ),
  },
  destructive: {
    label: "Destructive dialog",
    render: () => (
      <ClientFrame>
        <Backdrop />
        <ConfirmDialog
          open
          onOpenChange={() => {}}
          destructive
          title="Cancel the invitation to your contractor?"
          cancelLabel="Keep invitation"
          confirmLabel="Cancel invitation"
          onConfirm={() => {}}
          description="The link we sent stops working straight away. You can invite someone again later."
        />
      </ClientFrame>
    ),
  },
  kit: { label: "UI kit", render: () => <Kit /> },
  "client-shell": {
    label: "Client shell (every tab)",
    render: () => (
      <div className="flex min-h-dvh flex-col">
        <ClientTop name={NAME} projects={PROJECTS} />
        <main className="flex flex-1 flex-col bg-canvas pb-20 sm:pb-0">
          <ProjectHeader
            id="p1"
            title="Sample bungalow"
            status="active"
            address="Sample address, Enugu"
            badges={{ Milestones: 1 }}
            showAll
          />
        </main>
        <ClientNav showAll badges={{ Milestones: 1 }} />
      </div>
    ),
  },
  "contractor-shell": {
    label: "Contractor shell (every item)",
    render: () => (
      <div className="min-h-dvh bg-canvas">
        <ContractorTop name="Sample Contractor" showAll />
      </div>
    ),
  },
  "ops-shell": {
    label: "Ops shell (every item)",
    render: () => (
      <div className="flex min-h-dvh">
        <OpsSidebar name="Sample Ops" counts={{ vetting: 3, flagged_evidence: 2, disputes: 2 }} showAll />
        <div className="flex flex-1 flex-col bg-canvas">
          <OpsHeader title="Disputes" environment="local" />
        </div>
      </div>
    ),
  },
};

export function StatesGallery({ frame, slots }: { frame: string | null; slots: GallerySlots }) {
  const selected = frame ? FRAMES[frame] : undefined;
  if (selected) return <>{selected.render(slots)}</>;
  return (
    <main className="flex flex-col gap-4 p-8">
      <h1 className="type-h2 text-ink">States gallery (development only)</h1>
      <ul className="flex flex-col gap-2">
        {Object.entries(FRAMES).map(([key, f]) => (
          <li key={key}>
            <Link className="text-accent underline" href={`/dev/states?frame=${key}`}>
              {f.label}
            </Link>
          </li>
        ))}
      </ul>
    </main>
  );
}

export const GALLERY_FRAMES = Object.keys(FRAMES);
