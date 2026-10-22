import { CircleAlert, CircleCheck, Info, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "./cn";

// Alert and banner (components.md, Feedback): tinted background, a 4px left edge for ok, warn and bad, and
// neutral information on mist. role="alert" for warn and bad, role="status" otherwise.

export type AlertTone = "ok" | "warn" | "bad" | "info" | "neutral";

const STYLES: Record<AlertTone, { box: string; title: string; icon: LucideIcon; role: "alert" | "status" }> =
  {
    ok: { box: "border-l-4 border-ok-fg bg-ok-bg", title: "text-ok-fg", icon: CircleCheck, role: "status" },
    warn: {
      box: "border-l-4 border-warn-fg bg-warn-bg",
      title: "text-warn-fg",
      icon: TriangleAlert,
      role: "alert",
    },
    bad: {
      box: "border-l-4 border-bad-fg bg-bad-bg",
      title: "text-bad-fg",
      icon: CircleAlert,
      role: "alert",
    },
    info: { box: "bg-accent-tint", title: "text-info-fg", icon: Info, role: "status" },
    neutral: { box: "bg-mist", title: "text-ink", icon: Info, role: "status" },
  };

export function Alert({
  tone,
  title,
  children,
  action,
  className,
}: {
  tone: AlertTone;
  title?: ReactNode;
  children?: ReactNode;
  action?: ReactNode;
  className?: string;
}) {
  const style = STYLES[tone];
  const Icon = style.icon;
  return (
    <div
      role={style.role}
      className={cn("flex items-start gap-3 rounded-card px-4.5 py-4", style.box, className)}
    >
      <Icon aria-hidden strokeWidth={1.75} className={cn("mt-0.5 size-5 flex-none", style.title)} />
      <div className="flex flex-1 flex-col gap-1">
        {title ? <p className={cn("type-small font-semibold", style.title)}>{title}</p> : null}
        {children ? <div className="type-small text-slate">{children}</div> : null}
      </div>
      {action}
    </div>
  );
}
