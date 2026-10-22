"use client";

import { useId, useState } from "react";

import { api, call } from "@/common/api/client";
import { apiErrorFrom, NetworkError, toUiState, type UiState } from "@/common/api/errors";
import { useWrite } from "@/common/api/use-write";
import { safeNext } from "@/common/auth/roles";

import { type Channel, signInMessage } from "./sign-in-messages";

// Plain OTP sign-in (W1a). The designed AuthCard with every state (country picker, countdowns, consent)
// replaces this markup in the auth stage; the flow and the API calls stay.

type Mode = "phone" | "email";

async function verify(
  identifier: string,
  code: string,
): Promise<{ role: string | null; home: string | null }> {
  let response: Response;
  try {
    // Our own session route (not a backend path): it keeps the tokens in httpOnly cookies.
    response = await fetch("/api/session/verify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ identifier, code }),
    });
  } catch (cause) {
    throw new NetworkError(cause);
  }
  if (!response.ok) throw await apiErrorFrom(response);
  return (await response.json()) as { role: string | null; home: string | null };
}

export function SignInForm({ next, expired }: { next: string | null; expired: boolean }) {
  const ids = { identifier: useId(), code: useId(), message: useId() };
  const [mode, setMode] = useState<Mode>("phone");
  const [channel, setChannel] = useState<Exclude<Channel, "email">>("sms");
  const [identifier, setIdentifier] = useState("");
  const [code, setCode] = useState("");
  const [step, setStep] = useState<"identify" | "code">("identify");
  const [problem, setProblem] = useState<UiState | null>(null);
  const [noPortal, setNoPortal] = useState<string | null>(null);
  const sentBy: Channel = mode === "email" ? "email" : channel;

  const requestCode = useWrite(
    (input: { identifier: string; channel: Channel }, key: string) =>
      call(
        api().POST("/api/v1/auth/otp/request", {
          body: { identifier: input.identifier, channel: input.channel },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSuccess: () => {
        setProblem(null);
        setCode("");
        setStep("code");
      },
      onError: (error) => setProblem(toUiState(error)),
    },
  );

  const signIn = useWrite(
    (input: { identifier: string; code: string }) => verify(input.identifier, input.code),
    {
      onSuccess: ({ role, home }) => {
        if (!home) {
          setNoPortal(
            role === "supervisor"
              ? "Supervisors use the iBackHome Android app."
              : "The supplier portal isn't open yet.",
          );
          return;
        }
        window.location.assign(safeNext(next, home));
      },
      onError: (error) => setProblem(toUiState(error)),
    },
  );

  const message = problem ? signInMessage(problem, sentBy) : null;
  const codeCancelled = problem?.kind === "otp" && problem.problem !== "invalid_code";
  const busy = requestCode.isPending || signIn.isPending;

  return (
    <div className="flex flex-col gap-6">
      {expired && step === "identify" && !message && (
        <div role="status" className="rounded-control bg-info-bg p-4 text-info-fg">
          <p className="font-semibold">Please sign in again</p>
          <p>Sign in and we&apos;ll bring you back to this page. Nothing you started was approved or paid.</p>
        </div>
      )}
      {message && (
        <div id={ids.message} role="alert" className="rounded-control bg-bad-bg p-4 text-bad-fg">
          <p className="font-semibold">{message.title}</p>
          <p>{message.detail}</p>
        </div>
      )}
      {noPortal && (
        <div role="status" className="rounded-control bg-neutral-bg p-4 text-neutral-fg">
          <p>{noPortal}</p>
        </div>
      )}

      {step === "identify" ? (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            requestCode.mutate({ identifier: identifier.trim(), channel: sentBy });
          }}
        >
          <fieldset className="flex gap-4">
            <legend className="sr-only">Sign in with</legend>
            {(["phone", "email"] as const).map((m) => (
              <label key={m} className="flex min-h-target items-center gap-2">
                <input
                  type="radio"
                  name="mode"
                  checked={mode === m}
                  onChange={() => {
                    setMode(m);
                    setProblem(null);
                  }}
                />
                {m === "phone" ? "Phone" : "Email"}
              </label>
            ))}
          </fieldset>

          <label htmlFor={ids.identifier} className="font-semibold text-ink">
            {mode === "phone" ? "Phone number" : "Email address"}
          </label>
          <input
            id={ids.identifier}
            required
            type={mode === "phone" ? "tel" : "email"}
            autoComplete={mode === "phone" ? "tel" : "email"}
            placeholder={mode === "phone" ? "+44 7700 900000" : undefined}
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            aria-describedby={message ? ids.message : undefined}
            className="min-h-target rounded-control border border-line-strong bg-white px-3"
          />

          {mode === "phone" ? (
            <fieldset className="flex flex-col gap-2">
              <legend className="font-semibold text-ink">Send the code by</legend>
              {(["whatsapp", "sms"] as const).map((c) => (
                <label key={c} className="flex min-h-target items-center gap-2">
                  <input type="radio" name="channel" checked={channel === c} onChange={() => setChannel(c)} />
                  {c === "whatsapp" ? "WhatsApp" : "SMS"}
                </label>
              ))}
            </fieldset>
          ) : (
            <p className="type-small text-muted">
              The code arrives by email. Check spam if it doesn&apos;t show within a minute.
            </p>
          )}

          <button
            type="submit"
            disabled={busy}
            className="min-h-target rounded-control bg-primary px-4 font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
          >
            {problem?.kind === "send_failed" ? "Try again" : "Send code"}
          </button>
          <p className="type-small text-muted">
            Invited to a project? Use the phone number or email your invitation was sent to.
          </p>
        </form>
      ) : (
        <form
          className="flex flex-col gap-4"
          onSubmit={(e) => {
            e.preventDefault();
            signIn.mutate({ identifier: identifier.trim(), code });
          }}
        >
          <h2 className="type-h3 text-ink">Enter your code</h2>
          <p>
            We sent a 6-digit code by {sentBy === "email" ? "email" : sentBy === "sms" ? "SMS" : "WhatsApp"}{" "}
            to {identifier}.{" "}
            <button
              type="button"
              className="text-accent underline"
              onClick={() => {
                setStep("identify");
                setProblem(null);
              }}
            >
              Change
            </button>
          </p>
          <label htmlFor={ids.code} className="font-semibold text-ink">
            6-digit code
          </label>
          <input
            id={ids.code}
            required
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="\d{6}"
            maxLength={6}
            value={code}
            disabled={codeCancelled}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
            aria-describedby={message ? ids.message : undefined}
            className="min-h-target rounded-control border border-line-strong bg-white px-3 tracking-widest type-mono"
          />
          {codeCancelled ? (
            <button
              type="button"
              disabled={busy}
              onClick={() => requestCode.mutate({ identifier: identifier.trim(), channel: sentBy })}
              className="min-h-target rounded-control bg-primary px-4 font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              Send a new code
            </button>
          ) : (
            <button
              type="submit"
              disabled={busy || code.length !== 6}
              className="min-h-target rounded-control bg-primary px-4 font-semibold text-white hover:bg-primary-hover disabled:opacity-60"
            >
              Verify
            </button>
          )}
        </form>
      )}
    </div>
  );
}
