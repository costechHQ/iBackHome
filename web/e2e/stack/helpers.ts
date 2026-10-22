import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, type Browser, type Page } from "@playwright/test";

// Shared by the local-stack tests (IBH_STACK=1): sign in through the real form, reading the login code from the
// API log (ENVIRONMENT=local only).

const repoRoot = fileURLToPath(new URL("../../..", import.meta.url));

export function latestCode(identifier: string): string {
  const logs = execFileSync("docker", ["compose", "logs", "api", "--since", "2m"], {
    cwd: repoRoot,
    encoding: "utf8",
    maxBuffer: 64 * 1024 * 1024,
  });
  const escaped = identifier.replace(/[.+]/g, "\\$&");
  const code = [...logs.matchAll(new RegExp(`to ${escaped}: Your iBackHome code is (\\d{6})`, "g"))].at(
    -1,
  )?.[1];
  if (!code) throw new Error(`No login code for ${identifier} in the api log`);
  return code;
}

export async function signInByEmail(page: Page, email: string, next = "/projects") {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  await page.getByLabel("Email").check();
  await page.getByLabel("Email address").fill(email);
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await page.getByLabel("6-digit code").fill(latestCode(email));
  await page.getByRole("button", { name: "Verify" }).click();
  await page.waitForURL((url) => !url.pathname.startsWith("/sign-in"));
}

export async function axeViolations(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

// One browser session per person, kept between runs in web/.drive/ (gitignored): the backend allows only 3 login
// codes per email per 15 minutes. It is separate from the seed driver's session, and saved after every run with
// the latest (rotated) cookies, so a refresh token is never used twice.
const sessionFile = (who: string) =>
  fileURLToPath(new URL(`../../.drive/browser-${who.replace(/[^a-z0-9]/gi, "_")}.json`, import.meta.url));

export async function openSignedIn(
  browser: Browser,
  baseURL: string | undefined,
  email: string,
): Promise<Page> {
  const file = sessionFile(email);
  const context = await browser.newContext({ baseURL, storageState: existsSync(file) ? file : undefined });
  const page = await context.newPage();
  await page.goto("/projects");
  if (new URL(page.url()).pathname.startsWith("/sign-in")) await signInByEmail(page, email);
  return page;
}

export async function saveSession(page: Page, email: string) {
  const file = sessionFile(email);
  mkdirSync(dirname(file), { recursive: true });
  await page.context().storageState({ path: file });
  await page.context().close();
}
