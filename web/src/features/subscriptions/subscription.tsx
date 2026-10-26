"use client";

import { ExternalLink, Loader2, Lock } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";

import { ApiError } from "@/common/api/errors";
import { useProject } from "@/common/api/queries";
import { useOnline, useViewerTimeZone } from "@/common/layout/online";
import { ServerErrorContent } from "@/common/layout/system-pages";
import { CLIENT_CURRENCIES, formatMoney, type ClientCurrency } from "@/common/money";
import { formatDate } from "@/common/time";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { ConfirmDialog } from "@/common/ui/dialog";
import { SegmentedControl } from "@/common/ui/segmented";
import { Loading, Skeleton } from "@/common/ui/skeleton";
import { ToneChip } from "@/common/ui/status-chip";
import { Card, CardLabel } from "@/common/ui/surfaces";

import {
  useCancelSubscription,
  useRefreshAfterSubscription,
  useStartSubscription,
  useSubscription,
} from "./api";
import { describe } from "./state";

// The monthly supervision subscription at /projects/:id/subscription. The client picks GBP, USD or EUR and
// goes to Stripe Checkout (the price is shown there). Stripe sends them back with ?session_id or ?cancelled=1;
// the status only turns active when Stripe's webhook reaches the backend, so after Checkout this page keeps
// reading every few seconds. The final BoQ approval needs an active subscription (409 subscription_required).

export function SubscriptionPage({
  projectId,
  returnedFromStripe,
  cancelled,
}: {
  projectId: string;
  returnedFromStripe: boolean;
  cancelled: boolean;
}) {
  const timeZone = useViewerTimeZone();
  const online = useOnline();
  const project = useProject(projectId);
  const subscription = useSubscription(projectId, returnedFromStripe);
  const refresh = useRefreshAfterSubscription(projectId);
  const [currency, setCurrency] = useState<ClientCurrency>("GBP");
  const [confirming, setConfirming] = useState(false);
  const [checkoutUrl, setCheckoutUrl] = useState<string | null>(null);

  const start = useStartSubscription(projectId);
  const cancel = useCancelSubscription(projectId);

  const status = subscription.data?.status;
  useEffect(() => {
    // Stripe has confirmed: the BoQ and project views must read fresh data (the BoQ gate is open now).
    if (returnedFromStripe && status === "active") refresh();
  }, [returnedFromStripe, status, refresh]);

  if (project.isPending || subscription.isPending) {
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-8 sm:px-12">
        <Loading label="Loading the subscription">
          <Skeleton className="h-64 w-full" />
        </Loading>
      </div>
    );
  }
  if (!project.data || subscription.isError)
    return <ServerErrorContent reference={null} onRetry={() => void subscription.refetch()} />;

  const sub = subscription.data;
  const state = describe(sub);
  const confirmingPayment = returnedFromStripe && sub?.status !== "active";
  const startProblem = !start.error
    ? null
    : start.error instanceof ApiError && start.error.code === "stripe_not_configured"
      ? "Card payments aren't set up on this server yet. Nothing was charged."
      : start.error instanceof ApiError && start.error.status === 409
        ? "This project already has a subscription, or it is completed. Nothing was charged."
        : "We couldn't open the payment page. Nothing was charged. Try again.";

  return (
    <div className="mx-auto grid w-full max-w-6xl gap-6 px-4 py-8 sm:px-12 lg:grid-cols-3">
      <Card className="flex flex-col gap-5 p-6 sm:p-8 lg:col-span-2">
        <div className="flex flex-wrap items-center gap-3">
          <h1 className="type-h1 text-ink">{state.headline}</h1>
          <ToneChip label={state.label} tone={state.tone} />
        </div>
        <p className="text-slate">{state.detail}</p>

        {cancelled && !sub ? (
          <Alert tone="warn" title="You left the payment page">
            Nothing was charged. Start again when you&apos;re ready.
          </Alert>
        ) : null}

        {confirmingPayment ? (
          <Alert tone="info" title="Payment received. Waiting for Stripe to confirm.">
            <span className="flex items-center gap-2">
              <Loader2 aria-hidden strokeWidth={1.75} className="size-4 animate-spin" />
              Checking every few seconds. You can close this page; your subscription will show here.
            </span>
          </Alert>
        ) : null}

        {sub && sub.status !== "incomplete" ? (
          <dl className="flex flex-col divide-y divide-line rounded-card border border-line">
            <div className="flex justify-between gap-4 p-4">
              <dt className="text-slate">Every month</dt>
              <dd className="ibh-tabular font-semibold text-ink">
                {formatMoney(sub.amount_minor, sub.currency)}
              </dd>
            </div>
            {sub.current_period_end ? (
              <div className="flex justify-between gap-4 p-4">
                <dt className="text-slate">{sub.cancel_at_period_end ? "Ends" : "Renews"}</dt>
                <dd className="text-right text-ink">{formatDate(sub.current_period_end, timeZone)}</dd>
              </div>
            ) : null}
          </dl>
        ) : null}

        {state.canStart && !confirmingPayment ? (
          <>
            <SegmentedControl
              label="You pay in"
              value={currency}
              onChange={(c) => setCurrency(c)}
              segments={CLIENT_CURRENCIES.map((c) => ({ value: c, label: c }))}
            />
            {startProblem ? <Alert tone="bad" title={startProblem} /> : null}
            <Button
              size="lg"
              block
              loading={start.isPending || Boolean(checkoutUrl)}
              disabled={!online}
              onClick={() =>
                start.mutate(currency, {
                  onSuccess: (checkout) => {
                    setCheckoutUrl(checkout.checkout_url);
                    window.location.assign(checkout.checkout_url);
                  },
                })
              }
            >
              Continue to secure payment
              <ExternalLink aria-hidden strokeWidth={1.75} className="size-5" />
            </Button>
            {checkoutUrl ? (
              <a
                href={checkoutUrl}
                className="type-small flex items-center gap-1 self-start rounded-control font-semibold text-accent underline"
              >
                Nothing happening? Open the payment page
                <ExternalLink aria-hidden strokeWidth={1.75} className="size-4" />
              </a>
            ) : null}
            <p className="type-small text-center text-slate">
              Stripe shows the monthly price before you pay. iBackHome never sees your card details.
            </p>
          </>
        ) : null}

        {state.canCancel ? (
          <>
            {cancel.error ? (
              <Alert tone="bad" title="We couldn't cancel it. Nothing changed. Try again." />
            ) : null}
            <Button variant="outline" className="self-start" onClick={() => setConfirming(true)}>
              Cancel subscription
            </Button>
          </>
        ) : null}

        <Button asChild variant="text" className="self-start">
          <Link href={`/projects/${projectId}/setup`}>Back to set-up</Link>
        </Button>
      </Card>

      <aside>
        <Card className="flex flex-col gap-4 p-5">
          <CardLabel>What this pays for</CardLabel>
          <p className="type-small text-slate">
            A vetted supervisor visits your site and captures tamper-proof evidence, so you can see the work
            from anywhere. It is separate from the milestone money, which stays with the escrow partner until
            you approve a release.
          </p>
          <p className="type-small flex items-start gap-3 border-t border-line pt-3 text-slate">
            <Lock aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
            <span>You need an active subscription before the final BoQ approval starts the project.</span>
          </p>
        </Card>
      </aside>

      <ConfirmDialog
        open={confirming}
        onOpenChange={(o) => !cancel.isPending && setConfirming(o)}
        busy={cancel.isPending}
        title="Cancel the subscription?"
        description="It won't renew. Supervision continues until the end of the month you've already paid for."
        confirmLabel="Cancel subscription"
        cancelLabel="Keep it"
        destructive
        onConfirm={() => cancel.mutate(null, { onSettled: () => setConfirming(false) })}
      />
    </div>
  );
}
