"use client";

import * as Tooltip from "@radix-ui/react-tooltip";

import { formatDate, formatDateTime, formatTime, formatUtc } from "../time";

// A time in the viewer's zone (clients: their own; Nigerian roles: WAT), with the UTC time on hover and focus
// (components.md global rules). The <time> element carries the exact instant for assistive tech.

export function Time({
  iso,
  timeZone,
  format = "datetime",
}: {
  iso: string;
  timeZone: string;
  format?: "date" | "time" | "datetime";
}) {
  const text =
    format === "date"
      ? formatDate(iso, timeZone)
      : format === "time"
        ? formatTime(iso, timeZone)
        : formatDateTime(iso, timeZone);
  return (
    <Tooltip.Provider delayDuration={300}>
      <Tooltip.Root>
        <Tooltip.Trigger asChild>
          <time
            dateTime={iso}
            tabIndex={0}
            className="underline decoration-line-strong decoration-dotted underline-offset-2"
          >
            {text}
          </time>
        </Tooltip.Trigger>
        <Tooltip.Portal>
          <Tooltip.Content
            sideOffset={6}
            className="type-caption z-50 rounded-tag bg-navy-900 px-2 py-1 tracking-normal text-white shadow-raised"
          >
            {formatUtc(iso)}
            <Tooltip.Arrow className="fill-navy-900" />
          </Tooltip.Content>
        </Tooltip.Portal>
      </Tooltip.Root>
    </Tooltip.Provider>
  );
}
