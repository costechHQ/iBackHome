"use client";

import { useEffect, useState } from "react";

import { cn } from "./cn";

// Skeleton loader (components.md, Feedback): grey blocks in the shape of the real layout, a gentle pulse,
// and after 10 s a line saying it is taking longer.

export function Skeleton({ className }: { className?: string }) {
  return <div aria-hidden className={cn("animate-pulse rounded-control bg-neutral-bg", className)} />;
}

export const SLOW_AFTER_MS = 10_000;

/** Wraps skeleton blocks: announces loading once, and says so when it takes longer than 10 s. */
export function Loading({ label = "Loading", children }: { label?: string; children: React.ReactNode }) {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    const timer = setTimeout(() => setSlow(true), SLOW_AFTER_MS);
    return () => clearTimeout(timer);
  }, []);
  return (
    <div role="status" aria-live="polite" aria-busy="true" className="flex flex-col gap-4">
      <span className="sr-only">{label}</span>
      {children}
      {slow ? (
        <p className="type-small text-muted">This is taking longer than usual. Still loading…</p>
      ) : null}
    </div>
  );
}
