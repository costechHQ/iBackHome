"use client";

import { useQuery } from "@tanstack/react-query";
import { Check, ExternalLink, Loader2, Lock, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { ledgerQuery, shortId, useMilestones, useProject, type Milestone } from "@/common/api/queries";
import { useWrite } from "@/common/api/use-write";
import { moneyByMilestone } from "@/common/ledger";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { NotFoundContent, ServerErrorContent } from "@/common/layout/system-pages";
import { CLIENT_CURRENCIES, formatFxRate, formatMoney, type ClientCurrency } from "@/common/money";
import { formatDate, formatDateTime } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { ESCROW_LINE } from "@/common/ui/money-display";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";

// WEB-CLIENT-007 (first milestone) and 016 (the next ones) at /projects/:id/fund/:milestoneId. Before paying:
// the amount in the client's currency, the naira the escrow will hold, the fee and today's rate, from
// GET /funding/quote (nothing recorded). Then a Stripe Checkout session (POST /funding) and the hand-off.
// Stripe sends the client back with ?session_id (waiting for escrow until the webhook marks the milestone
// funded, then funded) or ?cancelled=1. Only the backend's one fee is shown: the design's "[X]%" and card
// processing lines are placeholders (PACKAGE-REPORT W-33). The client picks GBP, USD or EUR here.

type Stage = "before" | "redirecting" | "waiting" | "cancelled";

function useQuote(projectId: string, milestoneId: string, currency: ClientCurrency, enabled: boolean) {
  return useQuery({
    queryKey: ["funding-quote", projectId, milestoneId, currency],
    enabled,
    retry: false,
    staleTime: 60_000,
    queryFn: () =>
      call(
        api().GET("/api/v1/projects/{project_id}/funding/quote", {
          params: { path: { project_id: projectId }, query: { milestone_id: milestoneId, currency } },
        }),
      ),
  });
}

function Steps({ items }: { items: { label: string; detail: string; state: "done" | "now" | "later" }[] }) {
  return (
    <ol className="flex flex-col gap-3">
      {items.map((s, i) => (
        <li key={s.label} className="flex items-start gap-3">
          <span
            className={cn(
              "type-small flex size-7 flex-none items-center justify-center rounded-pill font-semibold",
              s.state === "done"
                ? "bg-navy-900 text-white"
                : s.state === "now"
                  ? "border-2 border-accent text-accent"
                  : "bg-mist text-ink",
            )}
          >
            {s.state === "done" ? <Check aria-hidden strokeWidth={2.5} className="size-4" /> : i + 1}
            <span className="sr-only">
              {s.state === "done" ? " (done)" : s.state === "now" ? " (in progress)" : ""}
            </span>
          </span>
          <span>
            <span className="block font-semibold text-ink">{s.label}</span>
            <span className="type-small text-slate">{s.detail}</span>
          </span>
        </li>
      ))}
    </ol>
  );
}

export function FundMilestone({
  projectId,
  milestoneId,
  sessionId,
  cancelled,
}: {
  projectId: string;
  milestoneId: string;
  sessionId: string | null;
  cancelled: boolean;
}) {
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const project = useProject(projectId);
  const [stage, setStage] = useState<Stage>(sessionId ? "waiting" : cancelled ? "cancelled" : "before");
  const milestones = useMilestones(projectId);
  const [currency, setCurrency] = useState<ClientCurrency>("GBP");
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);

  const all = (milestones.data ?? []) as Milestone[];
  const m = all.find((x) => x.id === milestoneId);
  const pending = m?.status === "pending";
  const quote = useQuote(projectId, milestoneId, currency, stage === "before" && pending);
  // After Stripe: keep checking until the webhook has the escrow hold the money.
  const waiting = stage === "waiting" && pending;
  useQuery({
    queryKey: ["funding-wait", projectId, milestoneId],
    enabled: waiting,
    refetchInterval: 3_000,
    queryFn: async () => {
      await milestones.refetch();
      return Date.now();
    },
  });
  // Read once the milestone is funded, so it has the payment in it.
  const ledger = useQuery({ ...ledgerQuery(projectId), enabled: Boolean(m) && !pending });

  const pay = useWrite(
    (input: { milestone_id: string; currency: ClientCurrency }, key: string) =>
      call(
        api().POST("/api/v1/projects/{project_id}/funding", {
          params: { path: { project_id: projectId } },
          body: input,
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSuccess: (checkout) => {
        setCheckoutUrl(checkout.checkout_url);
        setStage("redirecting");
        window.location.assign(checkout.checkout_url);
      },
    },
  );

  if (project.isPending || milestones.isPending) {
    return (
      <div className="mx-auto w-full max-w-6xl px-4 py-8 sm:px-12">
        <Loading label="Loading the milestone">
          <Skeleton className="h-80 w-full" />
        </Loading>
      </div>
    );
  }
  if (!project.data || !milestones.data)
    return <ServerErrorContent reference={null} onRetry={() => void milestones.refetch()} />;
  if (!m) return <NotFoundContent />;

  const ordered = [...all].sort((a, b) => a.sequence - b.sequence);
  const previous = ordered.filter((x) => x.sequence < m.sequence && x.released_at).at(-1);
  const projectHref = `/projects/${projectId}`;
  const milestoneHref = `/projects/${projectId}/milestones/${m.id}`;

  // Funded (or further): the success screen, with what was paid from the ledger.
  if (!pending) {
    const money = ledger.data ? moneyByMilestone(ordered, ledger.data.ledger).get(m.id) : undefined;
    const payment = money?.payment;
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-12">
        <Card className="flex flex-col gap-5 p-6 sm:p-8">
          <div className="flex flex-wrap items-center gap-3">
            <h1 className="type-h1 text-ink">{m.name} is funded</h1>
            <ToneChip label="Funded" tone="ok" />
          </div>
          <p className="text-slate">
            The escrow partner is holding {formatMoney(m.amount_minor, "NGN")}. Your contractor can start
            work, and the supervisor will visit to capture evidence. You&apos;ll be asked to approve when the
            supervisor verifies the stage.
          </p>
          <dl className="flex flex-col divide-y divide-line rounded-card border border-line">
            {payment ? (
              <div className="flex justify-between gap-4 p-4">
                <dt className="text-slate">You paid</dt>
                <dd className="ibh-tabular font-semibold text-ink">
                  {formatMoney(payment.paidMinor, payment.currency)}
                </dd>
              </div>
            ) : null}
            <div className="flex justify-between gap-4 p-4">
              <dt className="text-slate">Held for {m.name}</dt>
              <dd className="ibh-tabular text-right font-semibold text-ink">
                {payment ? `${formatMoney(payment.netMinor, payment.currency)} · ` : ""}
                {formatMoney(m.amount_minor, "NGN")}
              </dd>
            </div>
            {payment?.fxRate ? (
              <div className="flex justify-between gap-4 p-4">
                <dt className="text-slate">Rate recorded</dt>
                <dd className="text-right text-ink">
                  {formatFxRate(payment.fxRate, payment.currency)} · {formatDateTime(payment.at, timeZone)}
                </dd>
              </div>
            ) : null}
            {payment ? (
              <div className="flex justify-between gap-4 p-4">
                <dt className="text-slate">Reference</dt>
                <dd className="type-mono text-ink">{shortId(payment.ref)}</dd>
              </div>
            ) : null}
          </dl>
          <div className="flex flex-wrap gap-3">
            <Button asChild size="lg">
              <Link href={milestoneHref}>Go to the milestone</Link>
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href={`${projectHref}/ledger`}>View in ledger</Link>
            </Button>
          </div>
          <p className="type-small text-slate">{ESCROW_LINE}</p>
        </Card>
      </div>
    );
  }

  if (stage === "waiting") {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-12">
        <Card className="flex flex-col gap-5 p-6 sm:p-8" role="status" aria-live="polite">
          <p className="type-caption text-muted uppercase">Confirming with escrow</p>
          <h1 className="type-h1 text-ink">Payment received. Waiting for the escrow partner.</h1>
          <p className="text-slate">
            We&apos;re asking the escrow partner to hold the money for {m.name} — this usually takes a few
            minutes. You can close this page; we&apos;ll message you.
          </p>
          <Steps
            items={[
              { label: "Card payment", detail: "Stripe", state: "done" },
              { label: "Converted to naira", detail: formatMoney(m.amount_minor, "NGN"), state: "done" },
              { label: "Held by the escrow partner", detail: "Waiting for confirmation", state: "now" },
            ]}
          />
          <p className="type-small flex items-center gap-2 text-slate">
            <Loader2 aria-hidden strokeWidth={1.75} className="size-4 animate-spin" />
            Checking every few seconds
          </p>
          <Button asChild variant="outline" className="self-start">
            <Link href={projectHref}>Back to my project</Link>
          </Button>
          <p className="type-small text-slate">{ESCROW_LINE}</p>
        </Card>
      </div>
    );
  }

  if (stage === "cancelled") {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-12">
        <Card className="flex flex-col gap-5 p-6 sm:p-8">
          <span className="flex size-12 items-center justify-center rounded-pill bg-warn-bg text-warn-fg">
            <TriangleAlert aria-hidden strokeWidth={1.75} className="size-6" />
          </span>
          <h1 className="type-h1 text-ink">Your payment didn&apos;t go through</h1>
          <p className="text-slate">
            You left the payment page — nothing was charged, and {m.name} is still waiting to be funded.
          </p>
          <Card className="type-small bg-mist p-4 text-slate">
            <span className="font-semibold text-ink">Things that usually help</span> Try another card, or ask
            your bank to allow an international payment to Stripe. If you left the payment page on purpose,
            just start again when you&apos;re ready.
          </Card>
          <div className="flex flex-wrap gap-3">
            <Button size="lg" onClick={() => setStage("before")}>
              Try again
            </Button>
            <Button asChild size="lg" variant="outline">
              <Link href={projectHref}>Back to the project</Link>
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  if (stage === "redirecting") {
    return (
      <div className="mx-auto flex w-full max-w-3xl flex-col gap-6 px-4 py-8 sm:px-12">
        <Card className="flex flex-col items-start gap-4 p-6 sm:p-8" role="status">
          <h1 className="type-h1 text-ink">Taking you to Stripe</h1>
          <p className="text-slate">
            Stripe handles the card payment on its own secure page. iBackHome never sees your card details.
            You&apos;ll come back here when you&apos;re done.
          </p>
          {checkoutUrl ? (
            <a
              href={checkoutUrl}
              className="type-small flex items-center gap-1 rounded-control font-semibold text-accent underline"
            >
              Nothing happening? Open the payment page
              <ExternalLink aria-hidden strokeWidth={1.75} className="size-4" />
            </a>
          ) : null}
        </Card>
      </div>
    );
  }

  // Before you pay.
  const q = quote.data;
  const quoteProblem =
    quote.error instanceof ApiError && quote.error.status === 409
      ? "This milestone can't be funded right now."
      : quote.error
        ? "Today's amounts couldn't be loaded. Try again in a moment."
        : null;
  const payProblem = !pay.error
    ? null
    : pay.error instanceof ApiError && pay.error.code === "stripe_not_configured"
      ? "Card payments aren't set up on this server yet. Nothing was charged."
      : pay.error instanceof ApiError && pay.error.status === 409
        ? "This milestone was already funded or changed. Nothing was charged twice."
        : "We couldn't open the payment page. Nothing was charged. Try again.";

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-8 sm:px-12 lg:grid-cols-3">
      <Card className="flex flex-col gap-5 p-6 sm:p-8 lg:col-span-2">
        <div className="flex flex-col gap-1">
          <p className="type-small text-slate">
            Milestone {m.sequence} of {ordered.length}
            {previous?.released_at
              ? ` · ${previous.name} released ${formatDate(previous.released_at, timeZone)}`
              : ""}
          </p>
          <h1 className="type-h1 text-ink">Fund {m.name}</h1>
        </div>
        <SegmentedControl
          label="You pay in"
          value={currency}
          onChange={(c) => setCurrency(c)}
          segments={CLIENT_CURRENCIES.map((c) => ({ value: c, label: c }))}
        />
        {quoteProblem ? <Alert tone="warn" title={quoteProblem} /> : null}
        {!q ? (
          <Loading label="Working out today's amounts">
            <Skeleton className="h-32 w-full" />
          </Loading>
        ) : (
          <>
            <dl className="flex flex-col gap-3">
              <div className="flex justify-between gap-4">
                <dt className="text-slate">Milestone amount</dt>
                <dd className="text-right">
                  <span className="ibh-tabular block font-semibold text-ink">
                    {formatMoney(q.net_minor, q.currency)}
                  </span>
                  <span className="ibh-tabular type-small text-slate">
                    {formatMoney(q.amount_ngn_minor, "NGN")}
                  </span>
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-slate">
                  Funding fee ({(q.fee_bps / 100).toFixed(q.fee_bps % 100 ? 2 : 0)}%)
                </dt>
                <dd className="ibh-tabular text-ink">{formatMoney(q.fee_minor, q.currency)}</dd>
              </div>
              <div className="flex items-end justify-between gap-4 border-t border-line pt-3">
                <dt className="font-semibold text-ink">You pay today</dt>
                <dd className="ibh-tabular type-h2 text-ink">{formatMoney(q.total_minor, q.currency)}</dd>
              </div>
            </dl>
            <p className="type-small rounded-control bg-mist p-3 text-slate">
              <span className="font-semibold text-ink">{formatFxRate(q.fx_rate, q.currency)}</span> · rate set
              when you continue to payment and recorded on your receipt
            </p>
          </>
        )}
        <p className="type-small flex items-start gap-3 rounded-card border border-line p-4 text-slate">
          <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
          <span>
            <span className="font-semibold text-ink">{ESCROW_LINE}</span> Released to your contractor only
            after the supervisor verifies {m.name} and you approve.
          </span>
        </p>
        {payProblem ? <Alert tone="bad" title={payProblem} /> : null}
        <Button
          size="lg"
          block
          loading={pay.isPending}
          disabled={!q || !online}
          onClick={() => pay.mutate({ milestone_id: m.id, currency })}
        >
          Continue to secure payment
          <ExternalLink aria-hidden strokeWidth={1.75} className="size-5" />
        </Button>
        <p className="type-small text-center text-slate">
          You&apos;ll pay by card on Stripe&apos;s secure page, then come back here.
        </p>
      </Card>
      <aside>
        <Card className="flex flex-col gap-4 p-5">
          <CardLabel>What happens next</CardLabel>
          <Steps
            items={[
              { label: "Pay on Stripe", detail: `By card, in ${currency}.`, state: "later" },
              { label: "Escrow confirms the hold", detail: "Usually a few minutes.", state: "later" },
              {
                label: `${m.name} is funded`,
                detail: "Your contractor can start; your supervisor starts visits.",
                state: "later",
              },
            ]}
          />
          <p className="type-small border-t border-line pt-3 text-slate">
            Later milestones are funded one at a time. You can fund ahead if you like.
          </p>
        </Card>
      </aside>
    </div>
  );
}
