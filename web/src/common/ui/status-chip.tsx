import { chipFor, type Audience, type Entity, type Tone } from "../status";
import { cn } from "./cn";

// Status chip (components.md, Feedback): the only place status colour appears besides alerts, and the text
// always names the state. Label and tone come from state-to-ui.md through chipFor().

const TONE_CLASSES: Record<Tone, string> = {
  ok: "bg-ok-bg text-ok-fg",
  warn: "bg-warn-bg text-warn-fg",
  bad: "bg-bad-bg text-bad-fg",
  neutral: "bg-neutral-bg text-neutral-fg",
  // The sheet uses the accent tint behind info text.
  info: "bg-accent-tint text-info-fg",
};

export function ToneChip({
  label,
  tone,
  size = "default",
  className,
}: {
  label: string;
  tone: Tone;
  size?: "small" | "default";
  className?: string;
}) {
  return (
    <span
      className={cn(
        // 13px semibold on the sheet: the ops-body size, made semibold.
        "type-ops-body inline-flex items-center gap-1.5 rounded-pill px-2.5 font-semibold whitespace-nowrap",
        size === "small" ? "h-6" : "h-6.5",
        TONE_CLASSES[tone],
        className,
      )}
    >
      {label}
    </span>
  );
}

export function StatusChip({
  entity,
  state,
  audience,
  size,
  className,
}: {
  entity: Entity;
  state: string;
  audience: Audience;
  size?: "small" | "default";
  className?: string;
}) {
  const { label, tone } = chipFor(entity, state, audience);
  return <ToneChip label={label} tone={tone} size={size} className={className} />;
}
