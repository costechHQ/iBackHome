import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { axeViolations, drive, openSignedIn, saveSession } from "./helpers";

// W6b against the local stack, on a fresh project from the seed driver (milestone 1 funded): the project
// overview, funding milestone 2 (the real quote; Stripe isn't set up locally, so the hand-off answers 503 and
// the return from Stripe is shown with the driver's signed webhook doing the funding), a cancelled payment,
// the client home's attention list, the site map with the captures, and the weekly reports (no report exists
// locally, so the list request is answered here with the backend's shape).
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/money-home.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 300_000 });

const CLIENT = "adaeze.client@example.com";

let client: Page;
let projectId: string;
type M = { id: string; sequence: number; name: string; status: string };
let ms: M[];

async function shoot(page: Page, name: string, widths = [1280, 390]) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: test.info().outputPath(`${name}-${width}.png`), fullPage: true });
    expect(await axeViolations(page), `${name} at ${width}`).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}

test.beforeAll(async ({ browser }) => {
  test.setTimeout(300_000);
  projectId = drive("--new-project", "--to", "funded").projectId;
  client = await openSignedIn(browser, test.info().project.use.baseURL, CLIENT);
  ms = ((await (await client.request.get(`/api/v1/projects/${projectId}/milestones`)).json()) as M[]).sort(
    (a, b) => a.sequence - b.sequence,
  );
});
test.afterAll(async () => {
  if (client) await saveSession(client, CLIENT);
});

test("the project overview", async () => {
  await client.goto(`/projects/${projectId}`);
  await expect(
    client.getByText("1 of 3 milestones released").or(client.getByText("0 of 3 milestones released")),
  ).toBeVisible();
  await expect(client.getByText("In escrow now")).toBeVisible();
  await expect(client.getByText(`Next to fund: ${ms[1]!.name}.`)).toBeVisible();
  await shoot(client, "overview");
});

test("fund the next milestone: quote, Stripe, waiting for escrow, funded", async () => {
  const m = ms[1]!;
  await client.goto(`/projects/${projectId}/fund/${m.id}`);
  await expect(client.getByRole("heading", { name: `Fund ${m.name}` })).toBeVisible();
  await expect(client.getByText("You pay today")).toBeVisible();
  await expect(client.getByText(/^£1 = ₦/)).toBeVisible();
  await shoot(client, "fund-before");
  await client.getByRole("radio", { name: "USD" }).click();
  await expect(client.getByText(/^\$1 = ₦/)).toBeVisible();

  // Locally Stripe has no key: the designed message, nothing charged.
  await client.getByRole("button", { name: "Continue to secure payment" }).click();
  await expect(
    client.getByText("Card payments aren't set up on this server yet. Nothing was charged."),
  ).toBeVisible();

  // Back from Stripe: waiting, until the signed webhook (the driver) has the escrow hold the money.
  await client.goto(`/projects/${projectId}/fund/${m.id}?session_id=cs_test_${randomUUID()}`);
  await expect(client.getByText("Payment received. Waiting for the escrow partner.")).toBeVisible();
  await shoot(client, "fund-waiting", [1280]);
  drive("--project", projectId, "--milestone", "2", "--to", "funded");
  await expect(client.getByRole("heading", { name: `${m.name} is funded` })).toBeVisible({ timeout: 30_000 });
  await expect(client.getByText("You paid")).toBeVisible();
  await expect(client.getByText("Rate recorded")).toBeVisible();
  await shoot(client, "fund-funded");
});

test("a cancelled payment says nothing was charged", async () => {
  const m = ms[2]!;
  await client.goto(`/projects/${projectId}/fund/${m.id}?cancelled=1`);
  await expect(client.getByRole("heading", { name: "Your payment didn't go through" })).toBeVisible();
  await shoot(client, "fund-cancelled", [1280]);
  await client.getByRole("button", { name: "Try again" }).click();
  await expect(client.getByRole("heading", { name: `Fund ${m.name}` })).toBeVisible();
});

test("the client home lists what needs them", async () => {
  drive("--project", projectId, "--milestone", "1", "--to", "verified");
  await client.goto("/projects");
  await expect(client.getByRole("heading", { name: /Needs your attention/ })).toBeVisible();
  const item = client
    .getByRole("listitem")
    .filter({ hasText: `${ms[0]!.name} is verified — approve to release` });
  await expect(item.first()).toBeVisible();
  await expect(item.first().getByRole("link", { name: "Review and approve" })).toBeVisible();
  await shoot(client, "home");
});

test("the site map shows where evidence was captured", async () => {
  await client.goto(`/projects/${projectId}/site-map`);
  await expect(client.getByRole("region", { name: /Site map: the boundary/ })).toBeVisible();
  await expect(client.getByRole("heading", { name: /\d+ captures?/ })).toBeVisible();
  await expect(client.getByText(/^EV-/).first()).toBeVisible();
  await shoot(client, "site-map");
});

test("weekly reports: the list, the viewer, and drafts kept out", async () => {
  const week = "2026-10-12";
  const report = (id: string, status: string) => ({
    id,
    project_id: projectId,
    week_start: week,
    status,
    body_md: `# Weekly report\n\n${status === "draft" ? "UNREVIEWED DRAFT" : "Foundation was verified this week."}\n\n| Milestone | Status |\n|---|---|\n| Foundation | Verified |`,
    evidence_ids: [randomUUID()],
    pdf_url: null,
    sent_at: status === "sent" ? "2026-10-16T17:05:00Z" : null,
    created_at: "2026-10-16T16:00:00Z",
    updated_at: "2026-10-16T17:05:00Z",
  });
  const sent = report(randomUUID(), "sent");
  await client.route(`**/api/v1/projects/${projectId}/reports`, (route) =>
    route.fulfill({ json: [sent, report(randomUUID(), "draft")] }),
  );
  await client.goto(`/projects/${projectId}/reports`);
  await expect(client.getByText("Foundation was verified this week.")).toBeVisible();
  await expect(client.getByText("UNREVIEWED DRAFT")).toHaveCount(0);
  await expect(client.getByText("1 report", { exact: false })).toBeVisible();
  await shoot(client, "reports");
  await client.getByRole("link", { name: "Read" }).click();
  await expect(client.getByRole("heading", { name: "Weekly report" })).toBeVisible();
  await expect(client.getByRole("table")).toContainText("Foundation");
  await expect(client.getByText("AI-generated")).toBeVisible();
  await shoot(client, "report-viewer");
});
