"use client";

import { CircleCheck, Lock } from "lucide-react";
import { useId, type ReactNode } from "react";

import { Button } from "@/common/ui/button";
import { cn } from "@/common/ui/cn";

// The pieces the public application forms share (/supervisors, /contractors): a numbered section, the field
// grid, the consent box, the bot-trap field, the submit footer and the "received" panel. One look for both.

export const APPLY_GRID = "grid gap-x-5 gap-y-5 sm:grid-cols-2";

/** The form card itself: white, bordered, centred by the page around it. */
export const APPLY_CARD =
  "flex flex-col gap-8 rounded-card border border-line bg-white p-6 shadow-raised sm:p-10";

export function ApplyIntro({ title, lead }: { title: string; lead: string }) {
  return (
    <div className="flex flex-col items-center gap-2 text-center">
      <h3 className="type-h2 text-ink">{title}</h3>
      <p className="type-body-lg text-slate">{lead}</p>
    </div>
  );
}

export function ApplyGroup({
  step,
  title,
  hint,
  first,
  children,
}: {
  step: number;
  title: string;
  hint?: string;
  first?: boolean;
  children: ReactNode;
}) {
  const titleId = useId();
  return (
    <div
      role="group"
      aria-labelledby={titleId}
      className={cn("flex flex-col gap-5", !first && "border-t border-line pt-8")}
    >
      <div className="flex items-start gap-3">
        <span
          aria-hidden
          className="type-small flex size-8 flex-none items-center justify-center rounded-pill bg-navy-900 font-semibold text-white"
        >
          {step}
        </span>
        <div className="flex flex-col gap-1">
          <h3 id={titleId} className="type-h3 text-ink">
            {title}
          </h3>
          {hint ? <p className="type-small text-slate">{hint}</p> : null}
        </div>
      </div>
      {children}
    </div>
  );
}

export function ApplyConsent({
  id,
  checked,
  onChange,
  error,
  children,
}: {
  id: string;
  checked: boolean;
  onChange: (value: boolean) => void;
  error?: string | null;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 border-t border-line pt-8">
      <label htmlFor={id} className="flex items-start gap-3 rounded-card bg-canvas p-4 text-ink">
        <input
          id={id}
          type="checkbox"
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
          aria-invalid={error ? true : undefined}
          className="mt-1 size-5 flex-none"
        />
        <span>
          {children} <span className="text-muted">Required</span>
        </span>
      </label>
      {error ? <p className="type-small text-bad-fg">{error}</p> : null}
    </div>
  );
}

/** Off-screen and skipped by keyboards and screen readers. A bot that fills it is ignored by the backend. */
export function ApplyHoneypot({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <div aria-hidden className="sr-only">
      <label>
        Leave this empty
        <input
          type="text"
          name="website"
          tabIndex={-1}
          autoComplete="off"
          value={value}
          onChange={(e) => onChange(e.target.value)}
        />
      </label>
    </div>
  );
}

export function ApplySubmit({ pending, note }: { pending: boolean; note: string }) {
  return (
    <div className="flex flex-col items-center gap-3">
      <Button type="submit" size="lg" block loading={pending}>
        {pending ? "Sending…" : "Send my application"}
      </Button>
      <p className="type-small flex items-start gap-1.5 text-center text-muted">
        <Lock aria-hidden strokeWidth={1.75} className="size-4" />
        {note}
      </p>
    </div>
  );
}

export function ApplySuccess({ children }: { children: ReactNode }) {
  return (
    <div
      role="status"
      className="flex flex-col items-center gap-4 rounded-card border border-line bg-white p-8 text-center shadow-raised sm:p-12"
    >
      <span className="flex size-14 items-center justify-center rounded-pill bg-ok-bg">
        <CircleCheck aria-hidden strokeWidth={1.75} className="size-8 text-ok-fg" />
      </span>
      <h3 className="type-h2 text-ink">Application received</h3>
      {children}
    </div>
  );
}
