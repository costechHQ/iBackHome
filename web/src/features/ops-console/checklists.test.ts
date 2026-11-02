import { describe, expect, it } from "vitest";

import { itemsProblem, MAX_ITEMS, parseItems, templateKey } from "./checklists";

describe("checklist items", () => {
  it("takes one item per line, trimmed, without blanks or repeats", () => {
    expect(parseItems("  Rebar  spacing \n\nrebar spacing\nCover depth\n")).toEqual([
      "Rebar spacing",
      "Cover depth",
    ]);
  });
  it("needs at least one item and at most twenty", () => {
    expect(itemsProblem([])).toMatch(/at least one/i);
    expect(itemsProblem(Array.from({ length: MAX_ITEMS + 1 }, (_, i) => `Item ${i}`))).toMatch(/at most 20/i);
    expect(itemsProblem(["One"])).toBeNull();
  });
  it("finds a template by name whatever the case or spacing", () => {
    expect(templateKey("  Roofing   Works ")).toBe("roofing works");
  });
});
