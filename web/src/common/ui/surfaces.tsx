import type { LucideIcon } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { cn } from "./cn";

// Card, avatar and empty state (components.md, Data display and Feedback).

/** White card, 12px radius, 1px line border, subtle shadow. */
export function Card({ className, ...rest }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("rounded-card border border-line bg-white shadow-card", className)} {...rest} />;
}

/** Small caps heading used inside cards ("MONEY", "PEOPLE"). */
export function CardLabel({ className, ...rest }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={cn("type-caption text-muted uppercase", className)} {...rest} />;
}

const AVATAR_SIZES = {
  24: "size-6 type-caption",
  32: "size-8 type-caption",
  40: "size-10 type-small",
} as const;

export function initials(name: string | null | undefined): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "?";
  const first = words[0]?.[0] ?? "";
  const last = words.length > 1 ? (words.at(-1)?.[0] ?? "") : "";
  return (first + last).toUpperCase();
}

/** Circular initials. Always paired with the full name, so it is hidden from screen readers. */
export function Avatar({
  name,
  size = 32,
  className,
}: {
  name: string | null | undefined;
  size?: 24 | 32 | 40;
  className?: string;
}) {
  return (
    <span
      aria-hidden
      className={cn(
        "inline-flex flex-none items-center justify-center rounded-pill bg-mist font-semibold tracking-normal text-ink",
        AVATAR_SIZES[size],
        className,
      )}
    >
      {initials(name)}
    </span>
  );
}

/** Icon, a one-line reason the list is empty, and an action only when the person can act. */
export function EmptyState({
  icon: Icon,
  title,
  children,
  action,
  className,
}: {
  icon: LucideIcon;
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center gap-3 px-6 py-10 text-center", className)}>
      <span className="flex size-12 items-center justify-center rounded-pill border border-line bg-white text-navy-900">
        <Icon aria-hidden strokeWidth={1.75} className="size-6" />
      </span>
      <p className="type-h3 text-ink">{title}</p>
      {children ? <div className="max-w-md text-slate">{children}</div> : null}
      {action}
    </div>
  );
}
