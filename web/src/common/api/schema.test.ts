import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, expectTypeOf, it } from "vitest";

import type { paths } from "./schema";

const openapi = JSON.parse(
  readFileSync(fileURLToPath(new URL("./openapi.json", import.meta.url)), "utf8"),
) as {
  paths: Record<string, unknown>;
};

// The milestone release slice (W2–W3) is built on these routes.
const SLICE_PATHS = [
  "/api/v1/auth/otp/request",
  "/api/v1/auth/otp/verify",
  "/api/v1/auth/refresh",
  "/api/v1/me",
  "/api/v1/projects",
  "/api/v1/projects/{project_id}/milestones",
  "/api/v1/projects/{project_id}/evidence",
  "/api/v1/projects/{project_id}/ledger",
  "/api/v1/milestones/{milestone_id}/claim",
  "/api/v1/milestones/{milestone_id}/approve",
  "/api/v1/milestones/{milestone_id}/disputes",
  "/api/v1/disputes/{dispute_id}/resolve",
  "/api/v1/ops/queue",
] as const;

describe("generated API schema", () => {
  it("contains every route the release slice uses", () => {
    for (const path of SLICE_PATHS) expect(openapi.paths).toHaveProperty([path]);
  });

  it("types the routes from the same document", () => {
    expectTypeOf<paths>().toHaveProperty("/api/v1/milestones/{milestone_id}/approve");
    expectTypeOf<paths["/api/v1/milestones/{milestone_id}/approve"]>().toHaveProperty("post");
  });
});
