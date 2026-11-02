// The pure parts of the checklist templates screen (P7): the text box holds one item per line.
// Mirrors the backend (features/milestones): blanks dropped, repeats dropped (case ignored), at most 20 items.

export const MAX_ITEMS = 20;

/** The items typed in the box: trimmed, no blank lines, no repeats. */
export function parseItems(text: string): string[] {
  const seen = new Set<string>();
  const items: string[] = [];
  for (const line of text.split("\n")) {
    const item = line.split(/\s+/).filter(Boolean).join(" ");
    const key = item.toLowerCase();
    if (item && !seen.has(key)) {
      seen.add(key);
      items.push(item);
    }
  }
  return items;
}

/** Why the list can't be saved, or null when it can. */
export function itemsProblem(items: string[]): string | null {
  if (items.length === 0) return "Add at least one thing for the supervisor to check.";
  if (items.length > MAX_ITEMS) return `At most ${MAX_ITEMS} items; this has ${items.length}.`;
  return null;
}

/** How a milestone name finds its template: case and spacing don't matter. */
export function templateKey(name: string): string {
  return name.toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}
