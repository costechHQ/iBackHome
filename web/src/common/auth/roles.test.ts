import { describe, expect, it } from "vitest";

import { homeFor, safeNext } from "./roles";

describe("homeFor", () => {
  it("sends each web role to its portal and the others nowhere", () => {
    expect(homeFor("client")).toBe("/projects");
    expect(homeFor("contractor")).toBe("/c");
    expect(homeFor("ops")).toBe("/ops");
    expect(homeFor("supervisor")).toBeNull();
    expect(homeFor("supplier")).toBeNull();
  });
});

describe("safeNext", () => {
  it("keeps paths on this site", () => {
    expect(safeNext("/projects/p1/milestones?tab=1")).toBe("/projects/p1/milestones?tab=1");
  });

  it("refuses other origins, scheme tricks and API routes", () => {
    for (const bad of [
      "//evil.example",
      "/\\evil.example",
      "https://evil.example",
      "javascript:alert(1)",
      "/api/v1/me",
      "/api",
    ]) {
      expect(safeNext(bad, "/home"), bad).toBe("/home");
    }
    expect(safeNext(null)).toBe("/");
  });
});
