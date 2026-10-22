"use client";

import { useRef, type KeyboardEvent } from "react";

import { cn } from "./cn";

// Segmented control (components.md, Controls): an inline switch between views, a radio group underneath
// (arrow keys move between options, one tab stop).

export type Segment<T extends string> = { value: T; label: string; count?: number };

export function SegmentedControl<T extends string>({
  label,
  segments,
  value,
  onChange,
  className,
}: {
  label: string;
  segments: readonly Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  className?: string;
}) {
  const refs = useRef<(HTMLButtonElement | null)[]>([]);

  const move = (event: KeyboardEvent, index: number) => {
    const step =
      event.key === "ArrowRight" || event.key === "ArrowDown"
        ? 1
        : event.key === "ArrowLeft" || event.key === "ArrowUp"
          ? -1
          : 0;
    if (!step) return;
    event.preventDefault();
    const next = (index + step + segments.length) % segments.length;
    const segment = segments[next];
    if (!segment) return;
    onChange(segment.value);
    refs.current[next]?.focus();
  };

  return (
    <div
      role="radiogroup"
      aria-label={label}
      className={cn("inline-flex gap-1 rounded-control border border-line bg-white p-1", className)}
    >
      {segments.map((s, i) => {
        const selected = s.value === value;
        return (
          <button
            key={s.value}
            ref={(el) => {
              refs.current[i] = el;
            }}
            type="button"
            role="radio"
            aria-checked={selected}
            tabIndex={selected ? 0 : -1}
            onClick={() => onChange(s.value)}
            onKeyDown={(e) => move(e, i)}
            className={cn(
              "type-ops-body min-h-9 rounded-tag px-3 font-semibold",
              "",
              selected ? "bg-navy-900 text-white" : "text-slate hover:bg-mist",
            )}
          >
            {s.label}
            {s.count !== undefined ? (
              <span className={cn("ml-1", selected ? "" : "text-muted")}>{s.count}</span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
