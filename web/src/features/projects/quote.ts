// The quote checker's pure parts (WEB-CLIENT-006): the submitted BoQ written as quote text for
// POST /quotes/check, flagged lines first, the counts, and how much more than the index the flagged lines
// cost. Money in integer kobo; quantities are decimal strings with up to 3 places.

type BoqLine = {
  line_no: number;
  description: string;
  unit: string;
  quantity: string;
  unit_price_minor: number;
};
type BoqMilestone = { sequence: number; name: string; items: readonly BoqLine[] };

export type CheckedLine = {
  item: string;
  unit: string;
  quantity: string;
  unit_price_minor: number;
  line_total_minor: number;
  flag: string;
  index_price_minor?: number | null;
  percent_above_index?: string | null;
};

function naira(kobo: number): string {
  return `${Math.floor(kobo / 100)}.${String(kobo % 100).padStart(2, "0")}`;
}

/** One line per BoQ line, with its quantity and unit price together (the backend checks they appear so). */
export function boqAsQuoteText(milestones: readonly BoqMilestone[]): string {
  return milestones
    .flatMap((m) =>
      m.items.map(
        (l) =>
          `${m.sequence}.${l.line_no} ${l.description}: ${l.quantity} ${l.unit} at NGN ${naira(l.unit_price_minor)} each`,
      ),
    )
    .join("\n");
}

const ORDER: Record<string, number> = {
  over_index: 0,
  unit_differs: 1,
  not_found_in_quote: 2,
  not_in_index: 3,
  within_index: 4,
};

export function flaggedFirst<T extends CheckedLine>(lines: readonly T[]): T[] {
  return [...lines].sort((a, b) => (ORDER[a.flag] ?? 9) - (ORDER[b.flag] ?? 9));
}

export function counts(lines: readonly CheckedLine[]) {
  return {
    over: lines.filter((l) => l.flag === "over_index").length,
    within: lines.filter((l) => l.flag === "within_index").length,
    notInIndex: lines.filter((l) => l.flag === "not_in_index" || l.flag === "unit_differs").length,
  };
}

/** Quantity "48.000" times a kobo price, in kobo, rounded half up (BigInt, no floats). */
export function times(quantity: string, priceMinor: number): bigint {
  const [whole = "0", frac = ""] = quantity.trim().split(".");
  const scaled = BigInt(`${whole}${frac.padEnd(3, "0").slice(0, 3)}`); // thousandths
  const product = scaled * BigInt(priceMinor);
  return (product + 500n) / 1000n;
}

/** What the over-index lines cost above the index: Σ (quoted − index) × quantity. */
export function overIndexTotal(lines: readonly CheckedLine[]): bigint {
  return lines
    .filter((l) => l.flag === "over_index" && l.index_price_minor != null)
    .reduce((sum, l) => sum + times(l.quantity, l.unit_price_minor - (l.index_price_minor ?? 0)), 0n);
}
