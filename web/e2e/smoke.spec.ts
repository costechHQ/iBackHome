import { expect, test } from "@playwright/test";

test("the server is up and its health check is never cached", async ({ request }) => {
  const res = await request.get("/api/healthz");
  expect(res.status()).toBe(200);
  expect(res.headers()["cache-control"]).toContain("no-store");
});

test("the home page renders", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Far from home, never out of sight.");
});
