import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { axeViolations, openSignedIn, saveSession } from "./helpers";

// W7 against the local stack: the client creates a project for the seeded contractor (through the API); the
// contractor finds it under "Needs you", prices the BoQ in the editor (errors listed and linked, the price-index
// hint, a line moved between milestones), submits it, revises it once in review (which clears the approvals),
// and the client and ops approve it through the API, which locks it. Then the payouts and profile pages.
// The local price index is empty, so the browser is given one index price.
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/contractor-work.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 180_000 });

const CLIENT = "adaeze.client@example.com";
const CONTRACTOR = "+2348030000001";
const OPS = "ops@example.com";

let client: Page;
let contractor: Page;
let projectId: string;
const title = `Contractor test house ${Date.now()}`;

const INDEX = [
  {
    item_key: "cement-42-5r",
    item: "Cement 42.5R",
    unit: "bag",
    currency: "NGN",
    price_minor: 1_030_000,
    low_minor: 1_000_000,
    high_minor: 1_060_000,
    supplier_count: 3,
    last_observed_on: "2026-10-20",
    stale: false,
  },
];

async function shoot(page: Page, name: string, widths = [1280, 390]) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: test.info().outputPath(`${name}-${width}.png`), fullPage: true });
    expect(await axeViolations(page), `${name} at ${width}`).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}

async function as(page: Page, method: "put" | "post", path: string, data?: unknown) {
  const res = await page.request[method](path, {
    headers: { Origin: new URL(page.url()).origin, "Idempotency-Key": randomUUID() },
    data,
  });
  expect(res.status(), `${method} ${path}: ${await res.text()}`).toBeLessThan(300);
  return res.json();
}

test.beforeAll(async ({ browser }) => {
  const baseURL = test.info().project.use.baseURL;
  client = await openSignedIn(browser, baseURL, CLIENT);
  contractor = await openSignedIn(browser, baseURL, CONTRACTOR);
  await contractor.route("**/api/v1/price-index", (route) => route.fulfill({ json: INDEX }));
});
test.afterAll(async () => {
  if (client) await saveSession(client, CLIENT);
  if (contractor) await saveSession(contractor, CONTRACTOR);
});

test("a new project waits for the contractor's BoQ", async () => {
  const created = await as(client, "post", "/api/v1/projects", {
    title,
    address: "21 Test Close, Enugu",
    currency: "NGN",
    budget_minor: 50_000_000,
    contractor_phone: CONTRACTOR,
  });
  projectId = created.id;
  const [lat, lon] = [6.45 + Math.random() * 0.01, 7.5 + Math.random() * 0.01];
  const h = 0.0004;
  await as(client, "put", `/api/v1/projects/${projectId}/site`, {
    location: { lat, lon },
    geofence: {
      type: "Polygon",
      coordinates: [
        [
          [lon - h, lat - h],
          [lon + h, lat - h],
          [lon + h, lat + h],
          [lon - h, lat + h],
          [lon - h, lat - h],
        ],
      ],
    },
  });

  await contractor.goto("/c");
  const item = contractor.getByRole("listitem").filter({ hasText: `Price the work for ${title}` });
  await expect(item).toBeVisible();
  await item.getByRole("link", { name: "Price the BoQ" }).click();
  await expect(contractor).toHaveURL(`/c/projects/${projectId}/boq`);
  await expect(contractor.getByRole("heading", { name: "Price the work" })).toBeVisible();
});

test("the editor lists what to fix, links to it, and hints the index price", async () => {
  const p = contractor;
  await p.getByRole("button", { name: "Submit for review" }).click();
  const summary = p.getByRole("alert").filter({ hasText: "before you submit" });
  await expect(summary).toBeVisible();
  await expect(summary.getByRole("link", { name: "Milestone 1: give it a name" })).toBeVisible();
  await summary.getByRole("link", { name: "Milestone 1: add at least one line" }).click();
  await expect(p.getByLabel("Description , line 1.1")).toBeFocused();

  await p.getByLabel("Milestone 1 name").fill("Foundation");
  await p.getByLabel("Description , line 1.1").fill("Cement 42.5R");
  await p.getByLabel("Unit , line 1.1").fill("bag");
  await p.getByLabel("Quantity , line 1.1").fill("0");
  await p.getByLabel("Unit price ₦ , line 1.1").fill("12,000");
  // 12,000 against an index of 10,300 is 16.5% above: flagged to the client, never blocking.
  await expect(p.getByText("+16.5% · will be flagged")).toBeVisible();
  await p.getByRole("button", { name: "Submit for review" }).click();
  await expect(summary.getByRole("link", { name: "Line 1.1: quantity must be more than 0" })).toBeVisible();
  await expect(p.getByText("Must be more than 0, with up to 3 decimal places.")).toBeVisible();
  await p.getByLabel("Quantity , line 1.1").fill("640");
  await p.getByLabel("Unit price ₦ , line 1.1").fill("10,400");
  await expect(p.getByText("+1.0% · close to the index")).toBeVisible();

  await p.getByRole("button", { name: "Add line" }).click();
  await p.getByLabel("Description , line 1.2").fill("Roofing sheets");
  await p.getByLabel("Unit , line 1.2").fill("piece");
  await p.getByLabel("Quantity , line 1.2").fill("120");
  await p.getByLabel("Unit price ₦ , line 1.2").fill("8,500");

  await p.getByRole("button", { name: "Add milestone" }).click();
  await expect(p.getByLabel("Milestone 2 name")).toBeFocused();
  await p.getByLabel("Milestone 2 name").fill("Roofing");
  // Back to Foundation and move the roofing line into milestone 2.
  await p.getByRole("button", { name: /^1 · Foundation/ }).click();
  await p.getByLabel("Move line 1.2 to another milestone").selectOption({ label: "2 · Roofing" });
  await expect(p.getByLabel("Description , line 1.2")).toHaveCount(0);
  // 640 × ₦10,400 = ₦6,656,000; 120 × ₦8,500 = ₦1,020,000.
  await expect(p.getByText("₦7,676,000").first()).toBeVisible();
  await shoot(p, "boq-editor");
});

test("submitting counts as the contractor's approval; revising clears the approvals", async () => {
  const p = contractor;
  await p.getByRole("button", { name: "Submit for review" }).click();
  await expect(p.getByText("Submitted for review")).toBeVisible();
  await expect(p.getByText("In review")).toBeVisible();
  await shoot(p, "boq-in-review");

  await as(client, "post", `/api/v1/projects/${projectId}/boq/approve`);
  await p.reload();
  await p.getByRole("button", { name: "Revise BoQ" }).click();
  await expect(p.getByRole("alertdialog", { name: "Revise the BoQ?" })).toBeVisible();
  await p.getByRole("button", { name: "Revise BoQ" }).last().click();
  await expect(p.getByRole("heading", { name: "Revise the bill of quantities" })).toBeVisible();
  await p.getByLabel("Unit price ₦ , line 1.1").fill("10,300");
  await p.getByRole("button", { name: "Submit the revised BoQ" }).click();
  await expect(p.getByText("Submitted for review")).toBeVisible();

  // The client's earlier approval was cleared by the revision; only the contractor's is there.
  const boq = await (await client.request.get(`/api/v1/projects/${projectId}/boq`)).json();
  expect(boq.approvals.map((a: { role: string }) => a.role)).toEqual(["contractor"]);
  expect(boq.boq_total_minor).toBe(640 * 1_030_000 + 120 * 850_000);
});

test("approved by everyone, the BoQ is locked and the milestones exist", async ({ browser }) => {
  await as(client, "post", `/api/v1/projects/${projectId}/boq/approve`);
  const ops = await openSignedIn(browser, test.info().project.use.baseURL, OPS);
  await as(ops, "post", `/api/v1/projects/${projectId}/boq/approve`);
  await saveSession(ops, OPS);

  await contractor.goto(`/c/projects/${projectId}`);
  await expect(contractor).toHaveURL(`/c/projects/${projectId}/milestones`);
  await contractor.getByRole("link", { name: "BoQ", exact: true }).click();
  await expect(contractor.getByText("Approved", { exact: true })).toBeVisible();
  await expect(contractor.getByRole("button", { name: "Revise BoQ" })).toHaveCount(0);
  await shoot(contractor, "boq-locked");
});

test("payouts: released, held and not funded, the payout account, one row per milestone", async () => {
  await contractor.goto("/c");
  await contractor.getByRole("link", { name: "Payouts" }).click();
  await expect(contractor.getByRole("heading", { name: "Payouts" })).toBeVisible();
  await expect(contractor.getByText("Not funded yet")).toBeVisible();
  const table = contractor.getByRole("region", { name: "Payments for each milestone" });
  await expect(
    table.getByRole("row").filter({ hasText: "Roofing" }).filter({ hasText: title }),
  ).toBeVisible();
  await expect(
    contractor.getByText(/Held by a licensed escrow partner|held by a licensed escrow partner/),
  ).toBeVisible();
  await shoot(contractor, "payouts");
});

test("profile: the name can be edited, and the track record is counted, not typed", async () => {
  await contractor.getByRole("link", { name: "Profile" }).click();
  await expect(contractor.getByRole("heading", { name: "Track record on iBackHome" })).toBeVisible();
  await expect(contractor.getByText("You can’t edit these numbers.", { exact: false })).toBeVisible();
  await shoot(contractor, "profile");
  await contractor.getByRole("button", { name: "Edit profile" }).click();
  const name = contractor.getByLabel("Full name");
  const before = await name.inputValue();
  await name.fill("");
  await contractor.getByRole("button", { name: "Save" }).click();
  await expect(contractor.getByText("Enter your full name.")).toBeVisible();
  await name.fill(before || "Obinna Obi");
  await contractor.getByRole("button", { name: "Save" }).click();
  await expect(contractor.getByRole("button", { name: "Edit profile" })).toBeVisible();
});
