"use client";

import { useRef, type ClipboardEvent, type KeyboardEvent } from "react";

import { cn } from "@/common/ui/cn";

// The 6-digit code as six boxes (WEB-PUBLIC-010). Typing moves to the next box, Backspace on an empty box
// goes back, and pasting (or the phone's one-time-code suggestion) fills them all.

export function CodeBoxes({
  value,
  onChange,
  labelId,
  describedBy,
  invalid,
  disabled,
}: {
  value: string;
  onChange: (code: string) => void;
  labelId: string;
  describedBy?: string;
  invalid?: boolean;
  disabled?: boolean;
}) {
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length: 6 }, (_, i) => value[i] ?? "");

  const put = (from: number, typed: string) => {
    const incoming = typed.replace(/\D/g, "");
    if (!incoming) return;
    const next = [...digits];
    for (let i = 0; i < incoming.length && from + i < 6; i++) next[from + i] = incoming[i]!;
    onChange(next.join(""));
    refs.current[Math.min(from + incoming.length, 5)]?.focus();
  };

  const key = (event: KeyboardEvent<HTMLInputElement>, i: number) => {
    if (event.key === "Backspace" && !digits[i] && i > 0) {
      event.preventDefault();
      const next = [...digits];
      next[i - 1] = "";
      onChange(next.join(""));
      refs.current[i - 1]?.focus();
    } else if (event.key === "ArrowLeft" && i > 0) refs.current[i - 1]?.focus();
    else if (event.key === "ArrowRight" && i < 5) refs.current[i + 1]?.focus();
  };

  return (
    <div
      role="group"
      aria-labelledby={labelId}
      aria-describedby={describedBy}
      className="grid grid-cols-6 gap-2 sm:gap-3"
    >
      {digits.map((d, i) => (
        <input
          key={i}
          ref={(el) => {
            refs.current[i] = el;
          }}
          aria-label={`Digit ${i + 1} of 6`}
          aria-invalid={invalid ? true : undefined}
          inputMode="numeric"
          autoComplete={i === 0 ? "one-time-code" : "off"}
          disabled={disabled}
          value={d}
          onChange={(e) => {
            const typed = e.target.value;
            if (!typed) {
              const next = [...digits];
              next[i] = "";
              onChange(next.join(""));
              return;
            }
            // A digit typed into a full box replaces it; several at once (autofill) spread over the boxes.
            put(i, typed.length === 2 && d ? typed.replace(d, "") || d : typed);
          }}
          onPaste={(e: ClipboardEvent<HTMLInputElement>) => {
            e.preventDefault();
            put(i, e.clipboardData.getData("text"));
          }}
          onKeyDown={(e) => key(e, i)}
          onFocus={(e) => e.target.select()}
          className={cn(
            "type-h2 h-14 w-full rounded-control border bg-white text-center text-ink disabled:bg-mist disabled:text-muted",
            invalid ? "border-bad-fg" : "border-line-strong",
          )}
        />
      ))}
    </div>
  );
}
