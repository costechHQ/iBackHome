import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync } from "node:fs";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

import AxeBuilder from "@axe-core/playwright";
import { expect, type Browser, type Page } from "@playwright/test";

// Shared by the local-stack tests (IBH_STACK=1): sign in through the real form, reading the login code from the
// API log (ENVIRONMENT=local only).

const repoRoot = fileURLToPath(new URL("../../..", import.meta.url));
const webRoot = fileURLToPath(new URL("../..", import.meta.url));

/** Runs the seed driver (scripts/drive) and returns the project and milestone it drove. */
export function drive(...args: string[]): { projectId: string; milestoneId: string } {
  const out = execFileSync("bun", ["scripts/drive/index.ts", ...args], {
    cwd: webRoot,
    encoding: "utf8",
    timeout: 240_000,
    // On Windows, bun on PATH may be a shim that only a shell can start.
    shell: process.platform === "win32",
  });
  const match = /client\s+\/projects\/([0-9a-f-]{36})\/milestones\/([0-9a-f-]{36})/.exec(out);
  if (!match) throw new Error(`drive ${args.join(" ")}: no milestone in the output\n${out}`);
  return { projectId: match[1]!, milestoneId: match[2]! };
}

/** A new supervisor application waiting for ops (the driver's --applicant); returns the supervisor's id. */
export function driveApplicant(): string {
  const out = execFileSync("bun", ["scripts/drive/index.ts", "--applicant"], {
    cwd: webRoot,
    encoding: "utf8",
    timeout: 120_000,
    shell: process.platform === "win32",
  });
  const id = /applicant ([0-9a-f-]{36})/.exec(out)?.[1];
  if (!id)
    throw new Error(`drive --applicant: no applicant in the output
${out}`);
  return id;
}

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

/** Signs in by email, or by phone (SMS) when the identifier starts with +. */
export async function signIn(page: Page, identifier: string, next = "/projects") {
  await page.goto(`/sign-in?next=${encodeURIComponent(next)}`);
  if (identifier.startsWith("+")) {
    await page.getByRole("radio", { name: "Phone" }).click();
    await page.getByRole("textbox", { name: "Phone number" }).fill(identifier);
    await page.getByLabel("SMS").check();
  } else {
    await page.getByRole("radio", { name: "Email" }).click();
    await page.getByLabel("Email address").fill(identifier);
  }
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await page.getByLabel("Digit 1 of 6").fill(latestCode(identifier));
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
  identifier: string,
): Promise<Page> {
  const file = sessionFile(identifier);
  const context = await browser.newContext({ baseURL, storageState: existsSync(file) ? file : undefined });
  const page = await context.newPage();
  await page.goto("/projects");
  if (new URL(page.url()).pathname.startsWith("/sign-in")) {
    await signIn(page, identifier);
    // Kept at once, so a test that fails later doesn't spend another of the 3 codes per 15 minutes.
    mkdirSync(dirname(file), { recursive: true });
    await context.storageState({ path: file });
  }
  return page;
}

export async function saveSession(page: Page, email: string) {
  const file = sessionFile(email);
  mkdirSync(dirname(file), { recursive: true });
  await page.context().storageState({ path: file });
  await page.context().close();
}
