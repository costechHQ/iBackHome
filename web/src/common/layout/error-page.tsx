import { Ban, RefreshCw, Search, TriangleAlert, type LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

// Error page (components.md, Feedback; WEB-CLIENT-024 frames 1-4): what happened, whether money was affected,
// and what to do next, never only a code. Every portal uses the same layout inside its own shell.

export function ErrorPage({
  icon: Icon,
  title,
  children,
  actions,
  code,
}: {
  icon: LucideIcon;
  title: string;
  children: ReactNode;
  actions?: ReactNode;
  /** Small mono line under the actions: "Error 404", "Error 409 · same request recognised". */
  code: ReactNode;
}) {
  return (
    <section className="flex flex-1 flex-col items-center justify-center gap-5 bg-mist px-4 py-16 text-center">
      <span className="flex size-16 items-center justify-center rounded-pill border border-line bg-white text-navy-900">
        <Icon aria-hidden strokeWidth={1.75} className="size-7" />
      </span>
      <div className="flex max-w-md flex-col gap-3">
        <h1 className="type-h2 text-ink">{title}</h1>
        <div className="text-slate">{children}</div>
      </div>
      {actions ? <div className="flex flex-wrap justify-center gap-3">{actions}</div> : null}
      <p className="type-mono text-muted">{code}</p>
    </section>
  );
}

export const ERROR_ICONS = {
  notFound: Search,
  server: TriangleAlert,
  forbidden: Ban,
  conflict: RefreshCw,
} as const;
