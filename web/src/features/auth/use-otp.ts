"use client";

import { useCallback, useEffect, useState } from "react";

import { api, call } from "@/common/api/client";
import { apiErrorFrom, NetworkError, toUiState, type UiState } from "@/common/api/errors";
import { useWrite } from "@/common/api/use-write";

import { RESEND_AFTER_SECONDS } from "./otp";
import type { Channel } from "./sign-in-messages";

// The login-code flow behind every sign-in surface (the sign-in page, ops sign-in, signing back in after a
// session ends): ask for a code, then exchange it through our own session route, which keeps the tokens in
// httpOnly cookies. The backend decides everything; this only remembers what to show.

export type SignedIn = { role: string | null; home: string | null };

export type Sent = { identifier: string; channel: Channel; expiresAt: number; resendAt: number };

async function exchange(identifier: string, code: string): Promise<SignedIn> {
  let response: Response;
  try {
    response = await fetch("/api/session/verify", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ identifier, code }),
    });
  } catch (cause) {
    throw new NetworkError(cause);
  }
  if (!response.ok) throw await apiErrorFrom(response);
  return (await response.json()) as SignedIn;
}

/** A clock that ticks every second while something is counting down. */
export function useNow(active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return;
    const first = window.setTimeout(() => setNow(Date.now()), 0);
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => {
      window.clearTimeout(first);
      window.clearInterval(timer);
    };
  }, [active]);
  return now;
}

export function useOtp(onSignedIn: (result: SignedIn) => void) {
  const [sent, setSent] = useState<Sent | null>(null);
  const [problem, setProblem] = useState<{ state: UiState; channel: Channel } | null>(null);
  const [unavailable, setUnavailable] = useState<Channel[]>([]);
  // Rate limited: when asking again is allowed (from Retry-After).
  const [waitUntil, setWaitUntil] = useState<number | null>(null);

  const request = useWrite(
    (input: { identifier: string; channel: Channel }, key: string) =>
      call(
        api().POST("/api/v1/auth/otp/request", {
          body: { identifier: input.identifier, channel: input.channel },
          headers: { "Idempotency-Key": key },
        }),
      ),
    {
      onSuccess: (out, input) => {
        const now = Date.now();
        setSent({
          identifier: input.identifier,
          channel: input.channel,
          expiresAt: now + out.expires_in * 1000,
          resendAt: now + RESEND_AFTER_SECONDS * 1000,
        });
        setProblem(null);
        setWaitUntil(null);
      },
      onError: (error, input) => {
        const state = toUiState(error);
        setProblem({ state, channel: input.channel });
        if (state.kind === "channel_unavailable")
          setUnavailable((u) => (u.includes(input.channel) ? u : [...u, input.channel]));
        if (state.kind === "rate_limited")
          setWaitUntil(Date.now() + (state.retryAfterSeconds ?? 15 * 60) * 1000);
      },
    },
  );

  const verify = useWrite(
    (input: { identifier: string; code: string }) => exchange(input.identifier, input.code),
    {
      onSuccess: onSignedIn,
      onError: (error) => setProblem({ state: toUiState(error), channel: sent?.channel ?? "sms" }),
    },
  );

  const restart = useCallback(() => {
    setSent(null);
    setProblem(null);
  }, []);
  const clearProblem = useCallback(() => setProblem(null), []);

  return {
    sent,
    problem,
    unavailable,
    waitUntil,
    busy: request.isPending || verify.isPending,
    requesting: request.isPending,
    verifying: verify.isPending,
    send: (identifier: string, channel: Channel) => request.mutate({ identifier, channel }),
    verify: (code: string) => sent && verify.mutate({ identifier: sent.identifier, code }),
    /** Back to the first step ("Change", "Back", "Use email instead"). */
    restart,
    clearProblem,
  };
}

export type Otp = ReturnType<typeof useOtp>;
