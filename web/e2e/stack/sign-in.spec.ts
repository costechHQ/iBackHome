import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

// Signs in through the real form against the local Docker Compose API. Local only: with ENVIRONMENT=local the
// API writes login codes to its log, which this reads. Skipped unless IBH_STACK=1, so CI (no backend) never runs
// it. Each test uses a new email (a new sign-up is a client): the backend allows 3 codes per identifier per
// 15 minutes, so reusing one address would hit the limit. This leaves a few test users in the dev database.
//   IBH_STACK=1 bun run e2e e2e/stack

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");

const repoRoot = fileURLToPath(new URL("../../..", import.meta.url));

const newEmail = (tag: string) => `e2e-${tag}-${Date.now()}@example.com`;

function latestCode(identifier: string): string {
  const logs = execFileSync("docker", ["compose", "logs", "api", "--since", "2m"], {
    cwd: repoRoot,
    encoding: "utf8",
  });
  const codes = [
    ...logs.matchAll(
      new RegExp(`to ${identifier.replace(/[.+]/g, "\\$&")}: Your iBackHome code is (\\d{6})`, "g"),
    ),
  ];
  const code = codes.at(-1)?.[1];
  if (!code) throw new Error(`No login code for ${identifier} in the api log`);
  return code;
}

test("a client signs in by email, lands on their portal, and can't open ops", async ({ page }) => {
  const email = newEmail("signin");
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fprojects/);

  await page.getByLabel("Email").check();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();

  await page.getByLabel("6-digit code").fill(latestCode(email));
  await page.getByRole("button", { name: "Verify" }).click();
  await expect(page).toHaveURL(/\/projects$/);
  await expect(page.getByRole("heading", { name: "Signed in" })).toBeVisible();

  // Tokens stay in httpOnly cookies: page JavaScript can't see them.
  expect(await page.evaluate(() => document.cookie)).toBe("");

  await page.goto("/ops");
  await expect(page.getByRole("heading", { name: /This page is only for/ })).toBeVisible();

  await page.goto("/projects");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL(/\/sign-in$/);
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/sign-in\?next=/);
});

test("a wrong code shows the designed message", async ({ page }) => {
  const email = newEmail("wrong-code");
  await page.goto("/sign-in");
  await page.getByLabel("Email").check();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  const real = latestCode(email);
  await page.getByLabel("6-digit code").fill(real === "000000" ? "111111" : "000000");
  await page.getByRole("button", { name: "Verify" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("That code isn’t right.");
});
