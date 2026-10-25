import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { axeViolations, drive, openSignedIn, saveSession } from "./helpers";

// W8a against the local stack: the ops overview; the projects list and a project waiting for the ops BoQ
// approval (made here through the API), approved from its page, which makes it live; changing a site; a
// flagged capture (the driver sends one photo twice) accepted and another rejected with notes; the weekly
// reports, the price index, the vetting queue and the audit log, which shows the approval just made.
// Every page is checked with axe at 1440 px (the ops console is desktop only).
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/ops-console.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 300_000 });

const CLIENT = "adaeze.client@example.com";
const CONTRACTOR = "+2348030000001";
const OPS = "ops@example.com";

let ops: Page;
let client: Page;
let contractor: Page;
let reviewProject: string;
const title = `Ops review house ${Date.now()}`;

async function shoot(page: Page, name: string) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: test.info().outputPath(`${name}-1440.png`), fullPage: true });
  expect(await axeViolations(page), name).toEqual([]);
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
  ops = await openSignedIn(browser, baseURL, OPS);
  client = await openSignedIn(browser, baseURL, CLIENT);
  contractor = await openSignedIn(browser, baseURL, CONTRACTOR);
});
test.afterAll(async () => {
  if (ops) await saveSession(ops, OPS);
  if (client) await saveSession(client, CLIENT);
  if (contractor) await saveSession(contractor, CONTRACTOR);
});

test("a project whose BoQ waits only for ops", async () => {
  const created = await as(client, "post", "/api/v1/projects", {
    title,
    address: "8 Review Road, Enugu",
    currency: "NGN",
    budget_minor: 300_000_000,
    contractor_phone: CONTRACTOR,
  });
  reviewProject = created.id;
  const [lat, lon] = [6.44 + Math.random() * 0.01, 7.49 + Math.random() * 0.01];
  const h = 0.0004;
  const ring = [
    [lon - h, lat - h],
    [lon + h, lat - h],
    [lon + h, lat + h],
    [lon - h, lat + h],
    [lon - h, lat - h],
  ];
  await as(client, "put", `/api/v1/projects/${reviewProject}/site`, {
    location: { lat, lon },
    geofence: { type: "Polygon", coordinates: [ring] },
  });
  await as(contractor, "put", `/api/v1/projects/${reviewProject}/boq`, {
    milestones: [
      {
        name: "Foundation",
        items: [
          { description: "Foundation works", unit: "lot", quantity: "1", unit_price_minor: 120_000_000 },
        ],
      },
      {
        name: "Roofing",
        items: [{ description: "Roofing works", unit: "lot", quantity: "1", unit_price_minor: 150_000_000 }],
      },
    ],
  });
  await as(contractor, "post", `/api/v1/projects/${reviewProject}/boq/approve`);
  await as(client, "post", `/api/v1/projects/${reviewProject}/boq/approve`);
});

test("the overview shows the queues and the project that needs ops", async () => {
  await ops.goto("/ops");
  await expect(ops.getByRole("heading", { name: "Overview" })).toBeVisible();
  for (const label of ["Vetting", "Flagged evidence", "Disputes"]) {
    await expect(ops.getByRole("main").getByRole("link", { name: new RegExp(label) })).toBeVisible();
  }
  const row = ops.getByRole("row").filter({ hasText: title });
  await expect(row.getByText("Needs ops approval")).toBeVisible();
  await shoot(ops, "ops-overview");
});

test("the projects list finds it, and ops approve its BoQ, which makes it live", async () => {
  await ops.getByRole("link", { name: "Projects" }).first().click();
  await expect(ops.getByRole("heading", { name: "Projects" })).toBeVisible();
  await ops.getByLabel("Search").fill(title);
  await expect(ops.getByRole("row")).toHaveCount(2);
  await shoot(ops, "ops-projects");
  await ops.getByRole("link", { name: title }).click();
  await expect(ops.getByRole("heading", { name: title })).toBeVisible();
  await shoot(ops, "ops-project-review");
  await ops.getByRole("button", { name: "Approve BoQ as ops" }).click();
  const dialog = ops.getByRole("alertdialog", { name: "Approve this BoQ?" });
  await expect(dialog).toContainText("This is the last approval");
  await dialog.getByRole("button", { name: "Approve BoQ" }).click();
  await expect(ops.getByRole("table", { name: "Milestones" })).toBeVisible();
  await expect(ops.getByText("Active", { exact: true }).first()).toBeVisible();
  await shoot(ops, "ops-project-live");
});

test("ops can change a live project's site", async () => {
  await ops.getByRole("link", { name: "Change site" }).click();
  await expect(ops.getByRole("heading", { name: "Site and boundary" })).toBeVisible();
  await expect(ops.getByText("Saved · ops can change it")).toBeVisible();
  await expect(ops.getByRole("button", { name: "Edit site" })).toBeVisible();
  await shoot(ops, "ops-site");
});

test("flagged evidence: accept one, reject another with notes", async () => {
  drive("--new-project", "--to", "funded", "--flagged");
  drive("--new-project", "--to", "funded", "--flagged");
  await ops.goto("/ops/evidence");
  await expect(ops.getByRole("heading", { name: "Flagged evidence" })).toBeVisible();
  await shoot(ops, "ops-evidence-queue");
  const links = ops.getByRole("main").getByRole("link", { name: /^EV-/ });
  expect(await links.count()).toBeGreaterThanOrEqual(2);

  await links.first().click();
  await expect(ops.getByRole("img", { name: /Flagged capture/ })).toBeVisible();
  await expect(ops.getByText("Why it was flagged")).toBeVisible();
  await shoot(ops, "ops-evidence-review");
  await ops.getByRole("button", { name: "Accept" }).click();
  await expect(ops.getByText("It now counts as evidence")).toBeVisible();

  await ops.getByRole("button", { name: "Next in the queue" }).click();
  await ops.getByRole("button", { name: "Reject" }).click();
  await expect(ops.getByText("Say why it’s rejected")).toBeVisible();
  await ops.getByLabel(/Notes/).fill("The same photo as the one before it, sent twice.");
  await ops.getByRole("button", { name: "Reject" }).click();
  await expect(ops.getByText("It won’t count.")).toBeVisible();
});

test("weekly reports, price index and the vetting queue", async () => {
  await ops.getByRole("link", { name: "Weekly reports" }).click();
  await expect(ops.getByRole("heading", { name: "Weekly reports" })).toBeVisible();
  await expect(
    ops.getByRole("table", { name: "Weekly reports" }).or(ops.getByText("No weekly reports yet")),
  ).toBeVisible();
  await shoot(ops, "ops-reports");

  await ops.getByRole("link", { name: "Price index" }).click();
  await expect(ops.getByRole("heading", { name: "Price index", exact: true })).toBeVisible();
  await shoot(ops, "ops-price-index");

  await ops.getByRole("link", { name: "Vetting" }).first().click();
  await expect(ops.getByRole("heading", { name: "Vetting" })).toBeVisible();
  await shoot(ops, "ops-vetting");
});

test("the audit log finds the ops BoQ approval and shows what changed", async () => {
  await ops.getByRole("link", { name: "Audit log" }).click();
  await expect(ops.getByRole("heading", { name: "Audit log" })).toBeVisible();
  await ops.getByLabel("Action").fill("boq.approved");
  await ops.getByLabel("Object id").fill(reviewProject);
  await ops.getByRole("button", { name: "Search" }).click();
  const rows = ops.getByRole("table", { name: "Audit log entries" }).getByRole("row");
  await expect(rows).toHaveCount(4); // the header and three approvals: contractor, client, ops
  await rows.nth(1).getByRole("button").click();
  await expect(ops.getByText("Before", { exact: true })).toBeVisible();
  await expect(ops.getByText("After", { exact: true })).toBeVisible();
  await shoot(ops, "ops-audit");
});
