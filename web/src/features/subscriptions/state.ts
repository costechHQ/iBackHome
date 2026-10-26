// What the client sees for each subscription status. Pure, so the page and the tests share it. The backend
// decides the status (Stripe webhooks move it); the page only words it.

export type SubscriptionView = {
  status: "incomplete" | "active" | "past_due" | "canceled";
  cancel_at_period_end: boolean;
  paused_by_billing: boolean;
};

export type Tone = "ok" | "warn" | "bad" | "neutral";

export type SubscriptionState = {
  label: string;
  tone: Tone;
  headline: string;
  detail: string;
  /** The client can still cancel (an active one that is not already ending). */
  canCancel: boolean;
  /** The client can start a new checkout (none yet, an unfinished one, or a canceled one). */
  canStart: boolean;
};

export function describe(subscription: SubscriptionView | null | undefined): SubscriptionState {
  if (!subscription) {
    return {
      label: "Not started",
      tone: "neutral",
      headline: "Start your monthly supervision",
      detail:
        "Your project starts once the monthly supervision fee is set up. You pay on Stripe's secure page.",
      canCancel: false,
      canStart: true,
    };
  }
  switch (subscription.status) {
    case "incomplete":
      return {
        label: "Waiting for payment",
        tone: "warn",
        headline: "Finish setting up your subscription",
        detail: "Stripe hasn't confirmed a payment yet. If you left the payment page, start again.",
        canCancel: false,
        canStart: true,
      };
    case "past_due":
      return {
        label: "Payment overdue",
        tone: "bad",
        headline: "Your last payment didn't go through",
        detail: subscription.paused_by_billing
          ? "Work on your project is paused until the payment succeeds. Stripe will retry, and you can update your card from Stripe's emails."
          : "Stripe will retry the payment. Update your card from Stripe's emails to avoid a pause.",
        canCancel: false,
        canStart: false,
      };
    case "canceled":
      return {
        label: "Canceled",
        tone: "neutral",
        headline: "Your subscription has ended",
        detail: "You can start it again whenever you like.",
        canCancel: false,
        canStart: true,
      };
    case "active":
      return subscription.cancel_at_period_end
        ? {
            label: "Ending",
            tone: "warn",
            headline: "Your subscription ends after this month",
            detail: "Supervision continues until the end of the month you've paid for. It won't renew.",
            canCancel: false,
            canStart: false,
          }
        : {
            label: "Active",
            tone: "ok",
            headline: "Your supervision subscription is active",
            detail: "Your supervisor's visits are covered. It renews every month.",
            canCancel: true,
            canStart: false,
          };
  }
}

/** The BoQ approval answers 409 subscription_required when the last approval has no active subscription. */
export function needsSubscription(code: string | null | undefined): boolean {
  return code === "subscription_required";
}
