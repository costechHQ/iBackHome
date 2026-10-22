// One source of truth for status chips: label and tone per entity, state and viewer. The defaults come from
// state-to-ui.md (registry.generated.ts); the doc also names labels for specific viewers, listed here.
import type { Tone } from "./parse";
import { REGISTRY } from "./registry.generated";

export type { Tone } from "./parse";
export type Entity = keyof typeof REGISTRY;
export type Audience = "client" | "contractor" | "supervisor" | "supplier" | "ops";

export type Chip = { label: string; tone: Tone };

type Override = { entity: Entity; state: string; audience: readonly Audience[]; chip: Chip };

// Each label is quoted from the same row of state-to-ui.md (a test checks that it still appears there).
export const AUDIENCE_OVERRIDES: readonly Override[] = [
  {
    entity: "evidence",
    state: "flagged",
    audience: ["supervisor", "ops"],
    chip: { label: "Flagged", tone: "warn" },
  },
  {
    entity: "escrow_release",
    state: "failed",
    audience: ["ops"],
    chip: { label: "Release failed", tone: "bad" },
  },
  { entity: "project", state: "draft", audience: ["ops"], chip: { label: "Setup", tone: "neutral" } },
  {
    entity: "project",
    state: "boq_review",
    audience: ["contractor"],
    chip: { label: "In review", tone: "info" },
  },
  {
    entity: "material_order",
    state: "requested",
    audience: ["contractor"],
    chip: { label: "Requested", tone: "neutral" },
  },
  {
    entity: "material_order",
    state: "approved",
    audience: ["supplier"],
    chip: { label: "To deliver", tone: "neutral" },
  },
  {
    entity: "supervisor_vetting",
    state: "pending",
    audience: ["ops"],
    chip: { label: "In vetting", tone: "info" },
  },
  {
    entity: "supervisor_vetting",
    state: "approved",
    audience: ["ops"],
    chip: { label: "Vetted", tone: "ok" },
  },
  {
    // The doc's "Rejected, with reason": the reason is shown next to the chip, not inside it.
    entity: "supervisor_vetting",
    state: "rejected",
    audience: ["supervisor", "ops"],
    chip: { label: "Rejected", tone: "bad" },
  },
];

export class UnknownStatusError extends Error {}

/**
 * The chip for a state, as `audience` should see it. A state the doc doesn't list (or lists without a label,
 * such as a weekly report's "sent") throws, so a new backend status can't silently show the wrong chip.
 * A label the doc gives without a tone (a timeline step, or the client's soft "Still confirming") is neutral.
 */
export function chipFor(entity: Entity, state: string, audience: Audience): Chip {
  const override = AUDIENCE_OVERRIDES.find(
    (o) => o.entity === entity && o.state === state && o.audience.includes(audience),
  );
  if (override) return override.chip;

  const spec = (REGISTRY[entity] as Record<string, { label: string | null; tone: Tone | null }>)[state];
  if (!spec?.label) throw new UnknownStatusError(`No chip for ${entity}.${state} in state-to-ui.md`);
  return { label: spec.label, tone: spec.tone ?? "neutral" };
}

export function statesOf(entity: Entity): string[] {
  return Object.keys(REGISTRY[entity]);
}
