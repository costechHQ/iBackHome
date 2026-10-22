"use client";

import { ChevronLeft, Clock, Globe } from "lucide-react";
import { useId, useState, type ReactNode } from "react";

import { safeNext } from "@/common/auth/roles";
import { countryByIso } from "@/common/countries";
import { Alert } from "@/common/ui/alert";
import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";
import { SegmentedControl } from "@/common/ui/segmented";

import { CodeBoxes } from "./code-boxes";
import { CountryPicker } from "./country-picker";
import { clock, maskIdentifier, phoneIdentifier, secondsUntil } from "./otp";
import { signInMessage, type Channel } from "./sign-in-messages";
import { useNow, useOtp, type Otp } from "./use-otp";

// WEB-PUBLIC-010 AuthCard, and its ops variant (WEB-OPS-001): enter a phone number or email, then the 6-digit
// code. Every designed state comes from what the backend answers (sign-in-messages.ts); the design's
// "3 attempts left" isn't shown because the backend doesn't say (PACKAGE-REPORT B-1).

const CHANNEL_NAME: Record<Channel, string> = { sms: "SMS", whatsapp: "WhatsApp", email: "email" };
const fieldClass =
  "min-h-12 w-full rounded-control border border-line-strong bg-white px-3.5 type-body-lg text-ink placeholder:text-muted";

export function ProblemAlert({ otp, id }: { otp: Otp; id?: string }) {
  if (!otp.problem) return null;
  const message = signInMessage(otp.problem.state, otp.problem.channel);
  const soft = ["rate_limited", "channel_unavailable", "send_failed", "offline"].includes(
    otp.problem.state.kind,
  );
  return (
    <div id={id}>
      <Alert tone={soft ? "warn" : "bad"} title={message.title}>
        {message.detail}
      </Alert>
    </div>
  );
}

/** What was typed on step 1, kept by the card so "Back" and "Change" don't lose it. */
export type Draft = {
  mode: "phone" | "email";
  iso: string;
  phone: string;
  email: string;
  picked: "whatsapp" | "sms";
};

/** Step 1 for the public card: phone (with the channel) or email. */
function IdentifyStep({ otp, draft, edit }: { otp: Otp; draft: Draft; edit: (d: Partial<Draft>) => void }) {
  const ids = { phone: useId(), email: useId(), help: useId(), alert: useId(), channel: useId() };
  const { mode, iso, phone, email, picked } = draft;
  const setMode = (m: Draft["mode"]) => edit({ mode: m });
  const setIso = (v: string) => edit({ iso: v });
  const setPhone = (v: string) => edit({ phone: v });
  const setEmail = (v: string) => edit({ email: v });
  const setPicked = (v: Draft["picked"]) => edit({ picked: v });
  const waiting = otp.waitUntil !== null;
  const now = useNow(waiting);
  const wait = secondsUntil(otp.waitUntil, now);
  const channel: "whatsapp" | "sms" = otp.unavailable.includes(picked)
    ? picked === "whatsapp"
      ? "sms"
      : "whatsapp"
    : picked;
  const failed = otp.problem?.state.kind === "send_failed";

  return (
    <form
      className="flex flex-col gap-5"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        const dial = countryByIso(iso)?.dial ?? "44";
        if (mode === "phone") otp.send(phoneIdentifier(dial, phone), channel);
        else otp.send(email.trim(), "email");
      }}
    >
      <ProblemAlert otp={otp} id={ids.alert} />
      <SegmentedControl
        label="Sign in with"
        variant="soft"
        value={mode}
        onChange={(m) => {
          setMode(m);
          otp.clearProblem();
        }}
        segments={[
          { value: "phone", label: "Phone" },
          { value: "email", label: "Email" },
        ]}
      />
      {mode === "phone" ? (
        <>
          <div className="flex flex-col gap-1.5">
            <label
              id={`${ids.phone}-label`}
              htmlFor={ids.phone}
              className="type-small font-semibold text-ink"
            >
              Phone number
            </label>
            <div className="flex gap-2">
              <CountryPicker value={iso} onChange={setIso} labelId={`${ids.phone}-label`} />
              <input
                id={ids.phone}
                type="tel"
                autoComplete="tel-national"
                required
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
                aria-describedby={otp.problem ? ids.alert : undefined}
                className={fieldClass}
              />
            </div>
          </div>
          <fieldset className="flex flex-col gap-1.5">
            <legend className="type-small mb-1.5 font-semibold text-ink">Send the code by</legend>
            <div className="grid grid-cols-2 gap-2">
              {(["whatsapp", "sms"] as const).map((c) => {
                const off = otp.unavailable.includes(c);
                return (
                  <label
                    key={c}
                    className={cn(
                      "flex min-h-12 flex-wrap items-center gap-x-3 gap-y-0.5 rounded-control border px-3 py-2 sm:px-4",
                      off
                        ? "border-line bg-mist text-muted"
                        : channel === c
                          ? "border-2 border-navy-900 bg-white text-ink"
                          : "border-line-strong bg-white text-ink",
                    )}
                  >
                    <input
                      type="radio"
                      name={ids.channel}
                      checked={channel === c}
                      disabled={off}
                      onChange={() => setPicked(c)}
                    />
                    <span className="font-semibold">{c === "whatsapp" ? "WhatsApp" : "SMS"}</span>
                    {off ? (
                      <span className="type-caption tracking-normal text-warn-fg sm:ml-auto">
                        Unavailable
                      </span>
                    ) : null}
                  </label>
                );
              })}
            </div>
          </fieldset>
        </>
      ) : (
        <div className="flex flex-col gap-1.5">
          <label htmlFor={ids.email} className="type-small font-semibold text-ink">
            Email address
          </label>
          <input
            id={ids.email}
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            aria-describedby={otp.problem ? `${ids.alert} ${ids.help}` : ids.help}
            className={fieldClass}
          />
          <p id={ids.help} className="type-small text-muted">
            The code arrives by email. Check spam if it doesn&apos;t show within a minute.
          </p>
        </div>
      )}
      <Button
        type="submit"
        size="lg"
        block
        loading={otp.requesting}
        disabled={wait > 0 || (mode === "phone" ? !phone.trim() : !email.trim())}
      >
        {wait > 0 ? `Try again in ${clock(wait)}` : failed ? "Try again" : "Send code"}
      </Button>
      <p className="type-small text-muted">
        Invited to a project? Use the phone number or email your invitation was sent to.
      </p>
    </form>
  );
}

/** Step 1 for ops: work email only (WEB-OPS-001). */
function StaffEmailStep({ otp }: { otp: Otp }) {
  const ids = { email: useId(), alert: useId() };
  const [email, setEmail] = useState("");
  const now = useNow(otp.waitUntil !== null);
  const wait = secondsUntil(otp.waitUntil, now);
  return (
    <form
      className="flex flex-col gap-5"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        otp.send(email.trim(), "email");
      }}
    >
      <ProblemAlert otp={otp} id={ids.alert} />
      <div className="flex flex-col gap-1.5">
        <label htmlFor={ids.email} className="type-small font-semibold text-ink">
          Work email
        </label>
        <input
          id={ids.email}
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          aria-describedby={otp.problem ? ids.alert : undefined}
          className={fieldClass}
        />
      </div>
      <Button type="submit" size="lg" block loading={otp.requesting} disabled={wait > 0 || !email.trim()}>
        {wait > 0 ? `Try again in ${clock(wait)}` : "Email me a code"}
      </Button>
      <p className="type-small flex items-start gap-2 rounded-control bg-mist p-3 text-slate">
        <Globe aria-hidden strokeWidth={1.75} className="mt-0.5 size-4 flex-none" />
        For iBackHome staff only. Every action in the console is recorded in the audit log with your name,
        time and device.
      </p>
    </form>
  );
}

/**
 * Step 2: the code. `fixed` hides the ways to change who the code goes to (signing back in after a session
 * ended always uses the same account). `heading` lets a dialog use its own title element.
 */
export function CodeStep({
  otp,
  fixed = false,
  onUseEmail,
  heading = (text) => <h1 className="type-h2 text-ink">{text}</h1>,
}: {
  otp: Otp;
  fixed?: boolean;
  onUseEmail?: () => void;
  heading?: (text: string) => ReactNode;
}) {
  const ids = { label: useId(), alert: useId() };
  const [code, setCode] = useState("");
  const [forSent, setForSent] = useState(otp.sent);
  if (otp.sent !== forSent) {
    // A new code was sent: start again with empty boxes.
    setForSent(otp.sent);
    setCode("");
  }
  const sent = otp.sent;
  const now = useNow(Boolean(sent));
  if (!sent) return null;

  const left = secondsUntil(sent.expiresAt, now);
  const resendIn = secondsUntil(sent.resendAt, now);
  const state = otp.problem?.state;
  const cancelled = state?.kind === "otp" && state.problem === "too_many_attempts";
  const expired = left <= 0 || (state?.kind === "otp" && state.problem === "otp_expired");
  const dead = cancelled || expired;
  const wrong = state?.kind === "otp" && state.problem === "invalid_code";
  const otherPhone = sent.channel === "whatsapp" ? "sms" : sent.channel === "sms" ? "whatsapp" : null;
  const resend = (channel: Channel) => otp.send(sent.identifier, channel);

  return (
    <form
      className="flex flex-col gap-5"
      noValidate
      onSubmit={(e) => {
        e.preventDefault();
        if (dead) resend(sent.channel);
        else if (code.length === 6) otp.verify(code);
      }}
    >
      {!fixed ? (
        <button
          type="button"
          onClick={otp.restart}
          className="type-small flex items-center gap-1 self-start rounded-control font-semibold text-ink"
        >
          <ChevronLeft aria-hidden strokeWidth={2} className="size-4" />
          Back
        </button>
      ) : null}
      <div className="flex flex-col gap-2">
        {heading("Enter your code")}
        <p className="text-slate">
          We sent a 6-digit code by {CHANNEL_NAME[sent.channel]} to{" "}
          <span className="font-semibold text-ink">{maskIdentifier(sent.identifier)}</span>.
          {!fixed ? (
            <>
              {" "}
              <button type="button" onClick={otp.restart} className="rounded-control text-accent underline">
                Change
              </button>
            </>
          ) : null}
        </p>
      </div>
      <ProblemAlert otp={otp} id={ids.alert} />
      <p id={ids.label} className="sr-only">
        6-digit code
      </p>
      <CodeBoxes
        value={code}
        onChange={setCode}
        labelId={ids.label}
        describedBy={otp.problem ? ids.alert : undefined}
        invalid={wrong}
        disabled={dead}
      />
      <p className="type-small flex items-center gap-2 text-slate" aria-live="polite">
        <Clock aria-hidden strokeWidth={1.75} className="size-4" />
        {cancelled ? "Code cancelled" : expired ? "Expired" : `Code expires in ${clock(left)}`}
      </p>
      <Button
        type="submit"
        size="lg"
        block
        loading={dead ? otp.requesting : otp.verifying}
        disabled={!dead && code.length !== 6}
      >
        {dead ? "Send a new code" : "Verify"}
      </Button>
      <div className="flex flex-col gap-2 border-t border-line pt-4">
        <p className="type-small text-slate">Didn&apos;t get it?</p>
        <div className="type-small flex flex-wrap items-center gap-x-5 gap-y-2">
          {resendIn > 0 && !dead ? (
            <span className="font-semibold text-slate">Resend in {clock(resendIn)}</span>
          ) : (
            <button
              type="button"
              onClick={() => resend(sent.channel)}
              className="rounded-control font-semibold text-accent underline"
            >
              Resend code
            </button>
          )}
          {otherPhone && !otp.unavailable.includes(otherPhone) ? (
            <button
              type="button"
              onClick={() => resend(otherPhone)}
              className="rounded-control font-semibold text-accent underline"
            >
              Send by {CHANNEL_NAME[otherPhone]}
            </button>
          ) : null}
          {!fixed && sent.channel !== "email" && onUseEmail ? (
            <button
              type="button"
              onClick={onUseEmail}
              className="rounded-control font-semibold text-accent underline"
            >
              Use email instead
            </button>
          ) : null}
        </div>
      </div>
    </form>
  );
}

/** The whole card: who you are, then the code, then on to the portal (or back to `next`). */
export function SignInCard({
  variant = "public",
  next,
  expired = false,
}: {
  variant?: "public" | "ops";
  next: string | null;
  expired?: boolean;
}) {
  const [noPortal, setNoPortal] = useState<string | null>(null);
  const [draft, setDraft] = useState<Draft>({
    mode: "phone",
    iso: "GB",
    phone: "",
    email: "",
    picked: "whatsapp",
  });
  const edit = (d: Partial<Draft>) => setDraft((old) => ({ ...old, ...d }));
  const otp = useOtp(({ role, home }) => {
    if (!home) {
      setNoPortal(
        role === "supervisor"
          ? "Supervisors use the iBackHome Android app."
          : "The supplier portal isn't open yet.",
      );
      return;
    }
    window.location.assign(safeNext(next, home));
  });

  if (otp.sent) {
    return (
      <div className="flex flex-col gap-4">
        {noPortal ? (
          <Alert tone="neutral" title="Signed in">
            {noPortal}
          </Alert>
        ) : null}
        <CodeStep
          otp={otp}
          onUseEmail={() => {
            edit({ mode: "email" });
            otp.restart();
          }}
        />
      </div>
    );
  }
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-col gap-2">
        <h1 className="type-h2 text-ink">
          {variant === "ops" ? "Staff sign-in" : "Sign in or create an account"}
        </h1>
        {variant === "public" ? (
          <p className="text-slate">We&apos;ll send you a 6-digit code. There are no passwords.</p>
        ) : null}
      </div>
      {expired && !otp.problem ? (
        <Alert tone="info" title="Please sign in again">
          For your security, your session ended. Sign in and we&apos;ll bring you straight back to the page
          you were on. Nothing has changed on your project.
        </Alert>
      ) : null}
      {variant === "ops" ? (
        <StaffEmailStep otp={otp} />
      ) : (
        <IdentifyStep otp={otp} draft={draft} edit={edit} />
      )}
    </div>
  );
}
