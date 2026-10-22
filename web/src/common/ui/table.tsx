import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from "react";

import { cn } from "./cn";

// Table (components.md, Data display): column headers with scope="col", money right-aligned in tabular
// figures, a row highlight on hover. "dense" is the ops console's 13/19 type. Screens show a list instead
// below the md breakpoint where the design has a mobile frame.

export function Table({
  caption,
  dense,
  className,
  children,
}: {
  caption: string;
  dense?: boolean;
  className?: string;
  children: ReactNode;
}) {
  return (
    // A labelled, focusable region: when it scrolls sideways on a phone, keyboard users can scroll it too.
    <div
      role="region"
      aria-label={caption}
      tabIndex={0}
      className={cn("overflow-x-auto rounded-card border border-line bg-white", className)}
    >
      <table className={cn("w-full border-collapse text-left", dense ? "type-ops-body" : "type-small")}>
        <caption className="sr-only">{caption}</caption>
        {children}
      </table>
    </div>
  );
}

export function Th({
  numeric,
  className,
  ...rest
}: ThHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <th
      scope="col"
      className={cn(
        "type-caption border-b border-line px-3 py-2.5 whitespace-nowrap text-muted uppercase",
        numeric && "text-right",
        className,
      )}
      {...rest}
    />
  );
}

export function Tr({ className, ...rest }: HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr className={cn("border-b border-line last:border-b-0 hover:bg-row-highlight", className)} {...rest} />
  );
}

export function Td({
  numeric,
  className,
  ...rest
}: TdHTMLAttributes<HTMLTableCellElement> & { numeric?: boolean }) {
  return (
    <td
      className={cn("px-3 py-2.5 text-ink", numeric && "ibh-tabular text-right whitespace-nowrap", className)}
      {...rest}
    />
  );
}
