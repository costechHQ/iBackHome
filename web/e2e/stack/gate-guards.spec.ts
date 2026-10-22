import { expect, test, type Page } from "@playwright/test";

import { drive, openSignedIn, saveSession } from "./helpers";

// The web gate's guards: no screen offers a way around dual approval, each portal refuses the other roles,
// approving works from the keyboard alone, and the production-like server (no IBH_MOCKS) shows no mocked data.
// Makes one fresh project with a verified milestone and approves it.
//   IBH_STACK=1 bun run e2e e2e/stack/gate-guards.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 300_000 });

const CLIENT = "adaeze.client@example.com";
const CONTRACTOR = "+2348030000001";
const OPS = "ops@example.com";
// The second Playwright server: the same build without mocks or dev pages (playwright.config.ts).
const NO_MOCKS = process.env.PLAYWRIGHT_BASE_URL
  ? undefined
  : `http://127.0.0.1:${Number(process.env.PORT ?? 3010) + 1}`;

let client: Page;
let contractor: Page;
let ops: Page;
let projectId: string;
let milestoneId: string;

test.beforeAll(async ({ browser }) => {
  test.setTimeout(300_000);
  const baseURL = test.info().project.use.baseURL;
  client = await openSignedIn(browser, baseURL, CLIENT);
  contractor = await openSignedIn(browser, baseURL, CONTRACTOR);
  ops = await openSignedIn(browser, baseURL, OPS);
  ({ projectId, milestoneId } = drive("--new-project", "--to", "verified"));
});
test.afterAll(async () => {
  if (client) await saveSession(client, CLIENT);
  if (contractor) await saveSession(contractor, CONTRACTOR);
  if (ops) await saveSession(ops, OPS);
});

const forbidden = /This page is only for/;

test("each portal refuses the other roles", async () => {
  for (const [page, paths] of [
    [client, ["/c", "/ops/disputes"]],
    [contractor, ["/projects", `/projects/${projectId}/milestones/${milestoneId}`, "/ops/disputes"]],
    [ops, ["/projects", "/c"]],
  ] as const) {
    for (const path of paths) {
      await page.goto(path);
      await expect(page.getByRole("heading", { name: forbidden }), path).toBeVisible();
    }
  }
});

test("only the project's client can approve, and only once it's verified", async () => {
  const approveUI = (page: Page) =>
    page
      .getByRole("button", { name: /approve|release/i })
      .or(page.getByRole("link", { name: /approve|release/i }));

  // The client sees Approve on the verified milestone, and not on the others (pending).
  await client.setViewportSize({ width: 1280, height: 900 });
  await client.goto(`/projects/${projectId}/milestones/${milestoneId}`);
  // On a desktop it is a button that opens the confirm dialog (the phone has a link to the review page).
  await expect(client.getByRole("button", { name: "Approve release" }).first()).toBeVisible();
  const list = (await (await client.request.get(`/api/v1/projects/${projectId}/milestones`)).json()) as {
    id: string;
    status: string;
  }[];
  for (const m of list.filter((x) => x.status !== "verified")) {
    await client.goto(`/projects/${projectId}/milestones/${m.id}`);
    await expect(client.getByRole("link", { name: "Approve release" }), m.status).toHaveCount(0);
    await expect(client.getByRole("button", { name: "Approve release" }), m.status).toHaveCount(0);
  }

  // The contractor's screens offer no approve or release action on the same verified milestone.
  for (const path of [
    `/c/projects/${projectId}/milestones`,
    `/c/projects/${projectId}/milestones/${milestoneId}`,
  ]) {
    await contractor.goto(path);
    await contractor.waitForLoadState("networkidle");
    await expect(approveUI(contractor), path).toHaveCount(0);
  }

  // And the API, through the web app's proxy, refuses the contractor and ops.
  for (const page of [contractor, ops]) {
    await page.goto("/");
    const res = await page.request.post(`/api/v1/milestones/${milestoneId}/approve`, {
      headers: { Origin: new URL(page.url()).origin },
    });
    expect(res.status()).toBe(403);
  }
});

async function tabTo(page: Page, name: string) {
  for (let i = 0; i < 80; i++) {
    await page.keyboard.press("Tab");
    const text = await page.evaluate(() => document.activeElement?.textContent?.trim() ?? "");
    if (text === name) return;
  }
  throw new Error(`"${name}" isn't reachable with Tab`);
}

test("the client approves with the keyboard alone", async () => {
  await client.setViewportSize({ width: 1280, height: 900 });
  await client.goto(`/projects/${projectId}/milestones/${milestoneId}`);
  await tabTo(client, "Approve release");
  await client.keyboard.press("Enter");
  await expect(client.getByRole("alertdialog")).toBeVisible();
  await tabTo(client, "Confirm and release");
  await client.keyboard.press("Enter");
  await expect(client.getByRole("alertdialog")).toHaveCount(0);
  await expect
    .poll(
      async () =>
        (
          (await (await client.request.get(`/api/v1/projects/${projectId}/milestones`)).json()) as {
            id: string;
            status: string;
          }[]
        ).find((m) => m.id === milestoneId)?.status,
      { timeout: 30_000 },
    )
    .toMatch(/approved|released/);
});

test("without IBH_MOCKS, nothing mocked is shown", async () => {
  test.skip(!NO_MOCKS, "needs the second Playwright server (not with PLAYWRIGHT_BASE_URL)");
  // Mocks on (the test server): the mocked cards are there.
  await contractor.goto("/c");
  await expect(contractor.getByText("Paid to you")).toBeVisible();
  // The production-like server: the same pages, without them.
  await contractor.goto(`${NO_MOCKS}/c`);
  await expect(contractor.getByRole("heading", { level: 1 })).toBeVisible();
  await expect(contractor.getByText("Paid to you")).toHaveCount(0);
  await client.goto(`${NO_MOCKS}/projects/${projectId}/milestones/${milestoneId}`);
  await expect(client.getByRole("heading", { level: 1 }).first()).toBeVisible();
  await client.waitForLoadState("networkidle");
  await expect(client.getByText(/^Pays to/)).toHaveCount(0);
});
