"use client";

import { ChevronDown } from "lucide-react";
import {
  useEffect,
  useId,
  useRef,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from "react";

import { cn } from "./cn";

// Text input and select (components.md, Controls). The label is always visible; an error says what to do
// and uses red only for the border and the helper text.

const control =
  "min-h-12 w-full rounded-control border bg-white px-3.5 type-body-lg text-ink placeholder:text-muted " +
  "" +
  "disabled:bg-mist disabled:text-muted read-only:bg-mist";

type FieldProps = {
  label: string;
  help?: ReactNode;
  error?: string | null;
  className?: string;
};

function Help({ id, help, error }: { id: string; help?: ReactNode; error?: string | null }) {
  if (error) {
    return (
      <p id={id} className="type-small text-bad-fg">
        {error}
      </p>
    );
  }
  return help ? (
    <p id={id} className="type-small text-muted">
      {help}
    </p>
  ) : null;
}

export function TextField({
  label,
  help,
  error,
  className,
  id,
  ...input
}: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const auto = useId();
  const inputId = id ?? auto;
  const helpId = `${inputId}-help`;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={inputId} className="type-small font-semibold text-ink">
        {label}
      </label>
      <input
        id={inputId}
        aria-invalid={error ? true : undefined}
        aria-describedby={error || help ? helpId : undefined}
        className={cn(control, error ? "border-bad-fg" : "border-line-strong")}
        {...input}
      />
      <Help id={helpId} help={help} error={error} />
    </div>
  );
}

export function SelectField({
  label,
  help,
  error,
  className,
  id,
  children,
  ...select
}: FieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  const auto = useId();
  const selectId = id ?? auto;
  const helpId = `${selectId}-help`;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      <label htmlFor={selectId} className="type-small font-semibold text-ink">
        {label}
      </label>
      <div className="relative">
        <select
          id={selectId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error || help ? helpId : undefined}
          className={cn(control, "appearance-none pr-10", error ? "border-bad-fg" : "border-line-strong")}
          {...select}
        >
          {children}
        </select>
        <ChevronDown
          aria-hidden
          strokeWidth={1.75}
          className="pointer-events-none absolute top-1/2 right-3 size-5 -translate-y-1/2 text-muted"
        />
      </div>
      <Help id={helpId} help={help} error={error} />
    </div>
  );
}

export type FormProblem = { fieldId: string; message: string };

/**
 * "Fix 2 things to continue" (WEB-CLIENT-024 form validation): lists every problem as a link to its field and
 * takes focus when it appears, so keyboard and screen-reader users land on it.
 */
export function ErrorSummary({ problems }: { problems: readonly FormProblem[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (problems.length) ref.current?.focus();
  }, [problems]);
  if (!problems.length) return null;
  return (
    <div
      ref={ref}
      tabIndex={-1}
      role="alert"
      className="rounded-card border-l-4 border-bad-fg bg-bad-bg px-5 py-4"
    >
      <p className="type-small font-semibold text-ink">
        Fix {problems.length === 1 ? "1 thing" : `${problems.length} things`} to continue
      </p>
      <ul>
        {problems.map((p) => (
          <li key={p.fieldId}>
            <a href={`#${p.fieldId}`} className="type-small font-semibold text-bad-fg underline">
              {p.message}
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}
