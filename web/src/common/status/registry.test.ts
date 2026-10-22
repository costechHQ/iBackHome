import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import { AUDIENCE_OVERRIDES, chipFor, statesOf, UnknownStatusError } from "./index";
import { parseStateToUi, renderRegistry } from "./parse";
import { REGISTRY } from "./registry.generated";

const read = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");
const doc = read("../../../../Docs/design/04-api-mapping/state-to-ui.md");
const openapi = JSON.parse(read("../api/openapi.json")) as {
  components: { schemas: Record<string, { enum?: string[] }> };
};

describe("status registry", () => {
  it("matches state-to-ui.md (run `bun run gen:status` if this fails)", () => {
    expect(read("./registry.generated.ts").replace(/\r/g, "")).toBe(renderRegistry(parseStateToUi(doc)));
  });

  it("covers exactly the backend's milestone and vetting states", () => {
    expect(statesOf("milestone").sort()).toEqual(
      [...(openapi.components.schemas.MilestoneStatus?.enum ?? [])].sort(),
    );
    expect(statesOf("supervisor_vetting").sort()).toEqual(
      [...(openapi.components.schemas.VettingStatus?.enum ?? [])].sort(),
    );
  });

  it("skips the design-only order state that has no backend status", () => {
    expect(statesOf("material_order")).not.toContain("on_hold");
    expect(statesOf("material_order")).toEqual(["requested", "approved", "delivered", "paid", "cancelled"]);
  });

  it("gives the milestone chips of state-to-ui.md", () => {
    expect(chipFor("milestone", "claimed", "client")).toEqual({ label: "Claimed", tone: "warn" });
    expect(chipFor("milestone", "verified", "client")).toEqual({ label: "Verified", tone: "info" });
    expect(chipFor("milestone", "disputed", "contractor")).toEqual({ label: "Disputed", tone: "bad" });
    expect(chipFor("milestone", "funded", "ops")).toEqual({ label: "Funded", tone: "neutral" });
  });

  it("shows flagged evidence as 'Under review by iBackHome' to clients and 'Flagged' to ops", () => {
    expect(chipFor("evidence", "flagged", "client")).toEqual({
      label: "Under review by iBackHome",
      tone: "warn",
    });
    expect(chipFor("evidence", "flagged", "ops")).toEqual({ label: "Flagged", tone: "warn" });
  });

  it("keeps a failed release soft for the client and loud for ops", () => {
    expect(chipFor("escrow_release", "failed", "client")).toEqual({
      label: "Still confirming — your money is safe",
      tone: "neutral",
    });
    expect(chipFor("escrow_release", "failed", "ops")).toEqual({ label: "Release failed", tone: "bad" });
  });

  it("refuses states the doc doesn't label", () => {
    expect(() => chipFor("milestone", "teleported", "client")).toThrow(UnknownStatusError);
    expect(() => chipFor("weekly_report", "sent", "client")).toThrow(UnknownStatusError);
  });

  it("quotes every audience override from its own row of the doc", () => {
    for (const o of AUDIENCE_OVERRIDES) {
      const raw = (REGISTRY[o.entity] as Record<string, { raw: string }>)[o.state]?.raw ?? "";
      expect(raw, `${o.entity}.${o.state}`).toContain(o.chip.label);
    }
  });
});
