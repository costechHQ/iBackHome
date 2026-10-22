import { expect, test, type Page } from "@playwright/test";

import { axeViolations, openSignedIn, saveSession } from "./helpers";

// The client's milestone screens against the local stack, after the seed driver has put milestones into each
// state (web/README.md, "Seed driver"). Read-only except the last test, which approves a verified milestone.
//   IBH_STACK=1 bun run e2e e2e/stack/client-release.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial" });

const CLIENT = "adaeze.client@example.com";
type Milestone = { id: string; name: string; status: string; project_id: string };

let page: Page;
let byStatus: Map<string, Milestone>;

test.beforeAll(async ({ browser }) => {
  page = await openSignedIn(browser, test.info().project.use.baseURL, CLIENT);
  const projects = (await (await page.request.get("/api/v1/projects")).json()) as { items: { id: string }[] };
  byStatus = new Map();
  for (const p of projects.items) {
    const list = (await (
      await page.request.get(`/api/v1/projects/${p.id}/milestones`)
    ).json()) as Milestone[];
    for (const m of list) if (!byStatus.has(m.status)) byStatus.set(m.status, m);
  }
});
test.afterAll(async () => {
  if (page) await saveSession(page, CLIENT);
});

const url = (m: Milestone, sub = "") => `/projects/${m.project_id}/milestones/${m.id}${sub}`;

for (const status of ["pending", "funded", "claimed", "verified", "disputed", "released"]) {
  test(`milestone detail: ${status}`, async ({}, info) => {
    const m = byStatus.get(status);
    test.skip(!m, `no ${status} milestone: run the seed driver`);
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(url(m!));
      await expect(page.getByRole("heading", { name: m!.name, level: 1 }).first()).toBeVisible();
      await page.screenshot({ path: info.outputPath(`detail-${status}-${width}.png`), fullPage: true });
      expect(await axeViolations(page)).toEqual([]);
    }
    const approve = page
      .getByRole("button", { name: "Approve release" })
      .or(page.getByRole("link", { name: "Approve release" }));
    await page.setViewportSize({ width: 1280, height: 1000 });
    // Approve appears only on Verified (state-to-ui.md); a dispute leaves no approve button anywhere.
    if (status === "verified") await expect(approve.first()).toBeVisible();
    else await expect(approve).toHaveCount(0);
  });
}

test("evidence gallery and ledger", async ({}, info) => {
  const m = byStatus.get("released") ?? byStatus.get("verified");
  test.skip(!m, "run the seed driver");
  for (const [name, path] of [
    ["evidence", `/projects/${m!.project_id}/evidence`],
    ["ledger", `/projects/${m!.project_id}/ledger`],
    ["milestones", `/projects/${m!.project_id}/milestones`],
  ] as const) {
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 1000 });
      await page.goto(path);
      await page.waitForLoadState("networkidle");
      await page.screenshot({ path: info.outputPath(`${name}-${width}.png`), fullPage: true });
      expect(await axeViolations(page), `${name} at ${width}`).toEqual([]);
    }
  }
  await page.setViewportSize({ width: 1280, height: 1000 });
  await page.goto(`/projects/${m!.project_id}/ledger`);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "Download CSV" }).click();
  expect((await download).suggestedFilename()).toMatch(/^ibackhome-ledger-.*\.csv$/);
});

test("dispute: the raise form and the release-paused view", async ({}, info) => {
  const verified = byStatus.get("verified");
  const disputed = byStatus.get("disputed");
  test.skip(!verified || !disputed, "run the seed driver");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url(verified!, "/dispute"));
  await expect(page.getByRole("group", { name: "What's wrong?" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("dispute-form-390.png"), fullPage: true });
  expect(await axeViolations(page)).toEqual([]);
  await page.goto(url(disputed!, "/dispute"));
  await expect(page.getByRole("heading", { name: "Under review by iBackHome" })).toBeVisible();
  await page.screenshot({ path: info.outputPath("dispute-paused-390.png"), fullPage: true });
});

test("approve on a phone in three taps, then the receipt", async ({}, info) => {
  const m = byStatus.get("verified");
  test.skip(!m, "run the seed driver");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto(url(m!));
  await page.getByRole("link", { name: "Approve release" }).first().click(); // tap 1
  await expect(page).toHaveURL(new RegExp(`${m!.id}/approve$`));
  await page.screenshot({ path: info.outputPath("approve-review-390.png"), fullPage: true });
  await page.getByRole("button", { name: "Approve release" }).click(); // tap 2
  await page.screenshot({ path: info.outputPath("approve-confirm-390.png"), fullPage: true });
  expect(await axeViolations(page)).toEqual([]);
  await page.getByRole("button", { name: "Confirm and release" }).click(); // tap 3
  await expect(page).toHaveURL(new RegExp(`${m!.id}$`));
  await expect(page.getByText(/Releasing|is released|Released on/).first()).toBeVisible({ timeout: 30_000 });
  await page.screenshot({ path: info.outputPath("approved-390.png"), fullPage: true });
});
