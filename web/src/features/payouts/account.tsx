"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { CircleCheck } from "lucide-react";
import { useId, useState } from "react";

import { api, call } from "@/common/api/client";
import { ApiError } from "@/common/api/errors";
import { useWrite } from "@/common/api/use-write";
import { Alert } from "@/common/ui/alert";
import { cn } from "@/common/ui/cn";

// The contractor's payout account (backend #68): GET /banks, the account-name lookup, and PUT/GET
// /me/payout/recipient (only the last four digits are kept). Used by onboarding (WEB-CONTRACTOR-002), the
// payouts page (WEB-CONTRACTOR-008) and the profile (WEB-CONTRACTOR-009).

export type Recipient = { bank_name: string; account_name: string; account_number_masked: string };

export const payoutRecipientKey = ["me", "payout-recipient"] as const;

/** The saved account: data, `null` when there's none yet (404), undefined while loading or on error. */
export function usePayoutRecipient() {
  const query = useQuery({
    queryKey: payoutRecipientKey,
    retry: false,
    queryFn: () => call(api().GET("/api/v1/me/payout/recipient")),
  });
  const none = query.error instanceof ApiError && query.error.status === 404;
  return { ...query, recipient: none ? null : query.data };
}

const fieldClass =
  "min-h-12 w-full rounded-control border border-line-strong bg-white px-3.5 type-body-lg text-ink placeholder:text-muted";

/** Bank, account number, the name lookup and the save, without the buttons (each screen places its own). */
export function usePayoutForm(onSaved: (recipient: Recipient) => void) {
  const queries = useQueryClient();
  const [bank, setBank] = useState("");
  const [number, setNumber] = useState("");
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
        queries.setQueryData(payoutRecipientKey, recipient);
        setNumber("");
        onSaved(recipient);
      },
    },
  );
  const unavailable = [banks.error, lookup.error, save.error].some(
    (e) =>
      e instanceof ApiError && (e.code === "paystack_not_configured" || e.code === "paystack_unavailable"),
  );
  return {
    bank,
    setBank,
    number,
    setNumber,
    banks,
    lookup,
    save,
    unavailable,
    canSave: ready && Boolean(lookup.data),
    submit: () => {
      if (ready && lookup.data) save.mutate({ bank_code: bank, account_number: number });
    },
  };
}

export type PayoutForm = ReturnType<typeof usePayoutForm>;

export function PayoutFields({ form }: { form: PayoutForm }) {
  const ids = { bank: useId(), number: useId() };
  const { banks, lookup, save, unavailable } = form;
  return (
    <>
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
          value={form.bank}
          onChange={(e) => form.setBank(e.target.value)}
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
          value={form.number}
          onChange={(e) => form.setNumber(e.target.value.replace(/\D/g, ""))}
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
    </>
  );
}
