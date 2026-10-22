// The BoQ editor's pure parts (WEB-CONTRACTOR-004): the draft the contractor types, its totals, the checks the
// designer listed, the price-index hint and the body for PUT /projects/{id}/boq. Money is integer kobo (BigInt
// for products); quantities stay decimal strings with up to 3 places. Totals here are a preview with the
// server's rule (quantity × unit price, rounded half up); no total is sent, and the saved figures are the
// server's.

import { times } from "./quote";

export const LIMITS = { milestones: 20, lines: 500, name: 120, description: 500, unit: 20 } as const;

/** Index prices the editor compares with (GET /price-index). */
export type IndexEntry = {
  item_key: string;
  item: string;
  unit: string;
  currency: string;
  price_minor: number;
  stale: boolean;
};

export type DraftLine = { key: string; description: string; unit: string; quantity: string; price: string };
export type DraftMilestone = { key: string; name: string; lines: DraftLine[] };
export type Draft = { milestones: DraftMilestone[] };

/** A problem the contractor must fix before submitting: `field` is the input's id, `label` the summary link. */
export type Issue = { field: string; milestone: string; label: string; message: string };

type SavedBoq = {
  milestones: readonly {
    sequence: number;
    name: string;
    items: readonly {
      description: string;
      unit: string;
      quantity: string | number;
      unit_price_minor: number;
    }[];
  }[];
};

let counter = 0;
export function newKey(prefix: string): string {
  counter += 1;
  return `${prefix}${Date.now().toString(36)}${counter}`;
}

export function emptyLine(): DraftLine {
  return { key: newKey("l"), description: "", unit: "", quantity: "", price: "" };
}

export function emptyMilestone(): DraftMilestone {
  return { key: newKey("m"), name: "", lines: [emptyLine()] };
}

/** "1,250.50" naira from kobo, as the contractor would type it. */
export function nairaText(kobo: number): string {
  const whole = Math.floor(kobo / 100).toLocaleString("en-NG");
  const part = kobo % 100;
  return part ? `${whole}.${String(part).padStart(2, "0")}` : whole;
}

/** "12.500" -> "12.5"; the backend sends quantities with trailing zeros. */
export function quantityText(q: string | number): string {
  const s = String(q);
  return s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s;
}

/** The saved BoQ as a draft to edit; a new BoQ starts with one empty milestone. */
export function draftFrom(boq: SavedBoq | null | undefined): Draft {
  if (!boq || boq.milestones.length === 0) return { milestones: [emptyMilestone()] };
  return {
    milestones: [...boq.milestones]
      .sort((a, b) => a.sequence - b.sequence)
      .map((m) => ({
        key: newKey("m"),
        name: m.name,
        lines: m.items.map((l) => ({
          key: newKey("l"),
          description: l.description,
          unit: l.unit,
          quantity: quantityText(l.quantity),
          price: nairaText(l.unit_price_minor),
        })),
      })),
  };
}

/** A quantity above 0 with up to 3 decimal places (as the backend accepts), normalised; else null. */
export function parseQuantity(text: string): string | null {
  const s = text.trim().replace(/,/g, "");
  if (!/^\d{1,9}(\.\d{1,3})?$/.test(s)) return null;
  if (!/[1-9]/.test(s)) return null;
  return quantityText(s.replace(/^0+(?=\d)/, ""));
}

/** Naira typed as "10,400" or "10400.50" -> kobo; null unless above ₦0 with at most 2 decimal places. */
export function parseNaira(text: string): number | null {
  const s = text.trim().replace(/[₦,\s]/g, "");
  const match = /^(\d{1,11})(?:\.(\d{1,2}))?$/.exec(s);
  if (!match) return null;
  const kobo = Number(match[1]) * 100 + Number((match[2] ?? "").padEnd(2, "0"));
  return kobo > 0 ? kobo : null;
}

/** The line's total in kobo once its quantity and price are valid. */
export function lineTotal(line: DraftLine): bigint | null {
  const q = parseQuantity(line.quantity);
  const p = parseNaira(line.price);
  return q && p ? times(q, p) : null;
}

export function milestoneTotal(m: DraftMilestone): bigint {
  return m.lines.reduce((sum, l) => sum + (lineTotal(l) ?? 0n), 0n);
}

export function draftTotal(d: Draft): bigint {
  return d.milestones.reduce((sum, m) => sum + milestoneTotal(m), 0n);
}

export function lineCount(d: Draft): number {
  return d.milestones.reduce((n, m) => n + m.lines.length, 0);
}

/** A line with nothing typed in it (left out when submitting, never an error). */
export function isBlank(l: DraftLine): boolean {
  return !l.description.trim() && !l.unit.trim() && !l.quantity.trim() && !l.price.trim();
}

/** Input ids, so the error summary can link to the field. */
export const fieldId = {
  name: (m: DraftMilestone) => `boq-${m.key}-name`,
  line: (l: DraftLine, part: "description" | "unit" | "quantity" | "price") => `boq-${l.key}-${part}`,
};

/** Every problem with the draft, in the order they appear on screen (milestone, then line). */
export function issues(d: Draft): Issue[] {
  const out: Issue[] = [];
  if (d.milestones.length > LIMITS.milestones) {
    out.push({
      field: fieldId.name(d.milestones[LIMITS.milestones]!),
      milestone: d.milestones[LIMITS.milestones]!.key,
      label: `At most ${LIMITS.milestones} milestones`,
      message: `Combine milestones: a BoQ can have at most ${LIMITS.milestones}.`,
    });
  }
  const total = d.milestones.reduce((n, m) => n + m.lines.filter((l) => !isBlank(l)).length, 0);
  d.milestones.forEach((m, mi) => {
    const no = mi + 1;
    if (!m.name.trim()) {
      out.push({
        field: fieldId.name(m),
        milestone: m.key,
        label: `Milestone ${no}: give it a name`,
        message: "Give this milestone a name.",
      });
    }
    const lines = m.lines.filter((l) => !isBlank(l));
    if (lines.length === 0) {
      out.push({
        field: m.lines[0] ? fieldId.line(m.lines[0], "description") : fieldId.name(m),
        milestone: m.key,
        label: `Milestone ${no}: add at least one line`,
        message: "A milestone needs at least one line.",
      });
    }
    m.lines.forEach((l, li) => {
      if (isBlank(l)) return;
      const ref = `Line ${no}.${li + 1}`;
      const add = (part: "description" | "unit" | "quantity" | "price", label: string, message: string) =>
        out.push({ field: fieldId.line(l, part), milestone: m.key, label: `${ref}: ${label}`, message });
      if (!l.description.trim()) add("description", "describe the work", "Describe the work or material.");
      if (!l.unit.trim()) add("unit", "choose a unit", "Choose a unit.");
      if (!l.quantity.trim()) add("quantity", "enter a quantity", "Enter a quantity.");
      else if (!parseQuantity(l.quantity))
        add("quantity", "quantity must be more than 0", "Must be more than 0, with up to 3 decimal places.");
      if (!l.price.trim()) add("price", "enter a unit price", "Enter a unit price in naira.");
      else if (!parseNaira(l.price))
        add("price", "unit price must be more than ₦0", "Must be more than ₦0, with up to 2 decimal places.");
    });
  });
  if (total > LIMITS.lines) {
    const m = d.milestones[d.milestones.length - 1]!;
    out.push({
      field: fieldId.name(m),
      milestone: m.key,
      label: `At most ${LIMITS.lines} lines`,
      message: `A BoQ can have at most ${LIMITS.lines} lines.`,
    });
  }
  return out;
}

/** The body for PUT /projects/{id}/boq: blank lines left out, no totals (the server works them out). */
export function toSubmit(d: Draft) {
  return {
    milestones: d.milestones.map((m) => ({
      name: m.name.trim(),
      items: m.lines
        .filter((l) => !isBlank(l))
        .map((l) => ({
          description: l.description.trim(),
          unit: l.unit.trim(),
          quantity: parseQuantity(l.quantity) ?? l.quantity,
          unit_price_minor: parseNaira(l.price) ?? 0,
        })),
    })),
  };
}

// Index matching, as the backend's quote check does it (features/quotes/service.py): the same item key, else
// the one index item whose key sits inside the line's (or the other way round); units compared without a
// trailing "s"; flagged when more than 15% above the index.

export function itemKey(text: string): string {
  return text
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export function matchIndex(description: string, prices: readonly IndexEntry[]): IndexEntry | null {
  const key = itemKey(description);
  if (!key) return null;
  const exact = prices.find((p) => p.item_key === key);
  if (exact) return exact;
  const near = prices.filter(
    (p) => p.item_key && (`-${key}-`.includes(`-${p.item_key}-`) || `-${p.item_key}-`.includes(`-${key}-`)),
  );
  return near.length === 1 ? near[0]! : null;
}

export function sameUnit(a: string, b: string): boolean {
  const norm = (u: string) => itemKey(u).replace(/s$/, "");
  return norm(a) === norm(b);
}

export const FLAG_PERCENT = 15;

export type IndexHint =
  | { kind: "none" }
  | { kind: "unit_differs"; index: IndexEntry }
  | { kind: "priced"; index: IndexEntry; percent: string | null; over: boolean };

/** What the index says about a line while it's typed: nothing yet, a different unit, or the price compared. */
export function indexHint(line: DraftLine, prices: readonly IndexEntry[]): IndexHint {
  const index = matchIndex(line.description, prices);
  if (!index || index.currency !== "NGN") return { kind: "none" };
  if (line.unit.trim() && !sameUnit(line.unit, index.unit)) return { kind: "unit_differs", index };
  const price = parseNaira(line.price);
  if (!price) return { kind: "priced", index, percent: null, over: false };
  // One decimal place, rounded half up, in integers (as the backend's _percent_above).
  const tenths = (BigInt(price - index.price_minor) * 1000n) / BigInt(index.price_minor);
  const rem = (BigInt(price - index.price_minor) * 1000n) % BigInt(index.price_minor);
  const rounded =
    tenths + (2n * (rem < 0n ? -rem : rem) >= BigInt(index.price_minor) ? (rem < 0n ? -1n : 1n) : 0n);
  const sign = rounded < 0n ? "-" : "";
  const abs = rounded < 0n ? -rounded : rounded;
  const percent = `${sign}${abs / 10n}.${abs % 10n}`;
  return { kind: "priced", index, percent, over: 100 * price > (100 + FLAG_PERCENT) * index.price_minor };
}

/** Units the editor offers (the contractor may type another). */
export const COMMON_UNITS = [
  "bag",
  "tonne",
  "length",
  "roll",
  "piece",
  "trip",
  "m",
  "m²",
  "m³",
  "kg",
  "litre",
  "day",
  "lump sum",
] as const;
