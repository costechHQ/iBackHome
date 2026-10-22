import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

import { expect, test } from "@playwright/test";

import { axeViolations, openSignedIn, saveSession } from "./helpers";

// Signs in through the real form against the local Docker Compose API. Local only: with ENVIRONMENT=local the
// API writes login codes to its log, which this reads. Skipped unless IBH_STACK=1, so CI (no backend) never runs
// it. New sign-ups use a new email (a new sign-up is a client): the backend allows 3 codes per identifier per
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

test("a new client signs in by email, is asked to onboard first, and can't open ops", async ({ page }) => {
  const email = newEmail("client");
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fprojects/);

  await page.getByRole("radio", { name: "Email" }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await expect(page.getByText(/Code expires in \d:\d\d/)).toBeVisible();
  await expect(page.getByText(/Resend in 0:\d\d/)).toBeVisible();
  expect(await axeViolations(page)).toEqual([]);

  await page.getByLabel("Digit 1 of 6").fill(latestCode(email));
  await page.getByRole("button", { name: "Verify" }).click();
  // A new account goes to onboarding (consent first) before the portal; e2e/stack/onboarding.spec.ts finishes it.
  await expect(page).toHaveURL(/\/welcome$/);
  await expect(page.getByRole("heading", { name: "Your data, your consent" })).toBeVisible();
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/welcome$/);

  // A client can't open the ops console.
  await page.goto("/ops");
  await expect(page.getByRole("heading", { name: /This page is only for/ })).toBeVisible();

  // Signing out (here from onboarding) ends the session on this browser and says so.
  await page.goto("/welcome");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/\/signed-out$/);
  await expect(page.getByRole("heading", { name: "You've signed out" })).toBeVisible();
  await page.goto("/projects");
  await expect(page).toHaveURL(/\/sign-in\?next=/);
});

test("a wrong code shows the designed message", async ({ page }) => {
  const email = newEmail("wrong");
  await page.goto("/sign-in");
  await page.getByRole("radio", { name: "Email" }).click();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  const real = latestCode(email);
  await page.getByLabel("Digit 1 of 6").fill(real === "000000" ? "111111" : "000000");
  await page.getByRole("button", { name: "Verify" }).click();
  await expect(page.locator("main").getByRole("alert")).toContainText("That code isn’t right.");
});

test("an ops user signs in with their work email at /ops/sign-in", async ({ page }) => {
  // Needs the seeded ops user (backend/scripts/seed.py): run only with IBH_STACK_SEEDED=1.
  test.skip(
    !process.env.IBH_STACK_SEEDED,
    "needs a database seeded with backend/scripts/seed.py (IBH_STACK_SEEDED=1)",
  );
  const email = "ops2@example.com";
  await page.setViewportSize({ width: 1280, height: 800 });
  await page.goto("/ops");
  await expect(page).toHaveURL(/\/ops\/sign-in\?next=%2Fops$/);
  await expect(page.getByRole("heading", { name: "Staff sign-in" })).toBeVisible();
  expect(await axeViolations(page)).toEqual([]);
  await page.getByLabel("Work email").fill(email);
  await page.getByRole("button", { name: "Email me a code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await page.getByLabel("Digit 1 of 6").fill(latestCode(email));
  await page.getByRole("button", { name: "Verify" }).click();
  // /ops opens on the overview (WEB-OPS-002).
  await expect(page).toHaveURL(/\/ops$/);
  await expect(page.getByRole("navigation", { name: "Ops console" })).toBeAttached();
});

test("after the session ends, the client signs back in without leaving the page", async ({ browser }) => {
  test.skip(!process.env.IBH_STACK_SEEDED, "needs the seeded client (IBH_STACK_SEEDED=1)");
  const client = "adaeze.client@example.com";
  const page = await openSignedIn(browser, test.info().project.use.baseURL, client);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/projects");
  const here = page.url();

  // The session ends: the tokens are gone, and the next API call says 401.
  const context = page.context();
  const keep = (await context.cookies()).filter((c) => c.name !== "ibh_at" && c.name !== "ibh_rt");
  await context.clearCookies();
  await context.addCookies(keep);
  await page.evaluate(() => window.dispatchEvent(new CustomEvent("ibh:session-expired")));

  const dialog = page.getByRole("alertdialog", { name: "Please sign in again" });
  await expect(dialog).toBeVisible();
  await expect(dialog).toContainText(client);
  await page.screenshot({ path: test.info().outputPath("session-expired-390.png") });
  await dialog.getByRole("button", { name: "Send me a code" }).click();
  const code = page.getByRole("alertdialog", { name: "Enter your code" });
  // The code step appears once the code was sent, so it's in the API log by then.
  await expect(code).toBeVisible();
  await code.getByLabel("Digit 1 of 6").fill(latestCode(client));
  await code.getByRole("button", { name: "Verify" }).click();
  await expect(page.getByRole("alertdialog")).toHaveCount(0);
  expect(page.url()).toBe(here);

  // A new session: the page loads signed in.
  await page.reload();
  await expect(page).toHaveURL(here);
  await saveSession(page, client);
});
