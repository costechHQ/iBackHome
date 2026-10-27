"use client";

import { useEffect, useRef, type ReactNode } from "react";

import { cn } from "@/common/ui/cn";

// Fades and lifts its children in the first time they scroll into view. The hidden starting state lives in
// globals.css and applies only when scripting is on and the visitor hasn't asked for less motion, so the
// content is always readable without JavaScript.
export function Reveal({
  children,
  delay = 0,
  className,
}: {
  children: ReactNode;
  /** Milliseconds to wait once visible, to stagger a row of cards. */
  delay?: number;
  className?: string;
}) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      el.classList.add("is-in");
      return;
    }
    const seen = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          el.classList.add("is-in");
          seen.disconnect();
        }
      },
      { threshold: 0.15 },
    );
    seen.observe(el);
    return () => seen.disconnect();
  }, []);

  return (
    <div
      ref={ref}
      className={cn("ibh-reveal", className)}
      style={delay ? { transitionDelay: `${delay}ms` } : undefined}
    >
      {children}
    </div>
  );
}
