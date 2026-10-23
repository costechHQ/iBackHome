import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { axeViolations, openSignedIn, saveSession } from "./helpers";

// W6a against the local stack: the client creates a project and invites the seeded contractor, pins the site
// and draws its boundary (keyboard and map), the contractor puts up a BoQ and approves it with ops (through the
// API), and the client reviews it, checks it against the price index (the AI answer is given here, since the
// model needs a key) and gives the final approval, which makes the project active.
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/project-setup.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 180_000 });

const CLIENT = "adaeze.client@example.com";
const CONTRACTOR = "+2348030000001";
const OPS = "ops@example.com";

let client: Page;
let projectId: string;
const title = `Set-up test house ${Date.now()}`;

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
  return res;
}

test.beforeAll(async ({ browser }) => {
  client = await openSignedIn(browser, test.info().project.use.baseURL, CLIENT);
});
test.afterAll(async () => {
  if (client) await saveSession(client, CLIENT);
});

test("create a project and invite the contractor", async () => {
  await client.goto("/projects");
  // The client home (WEB-CLIENT-008) lists the projects under "Your projects".
  await expect(client.getByRole("heading", { name: "Your projects" })).toBeVisible();
  await shoot(client, "projects");

  await client.getByRole("link", { name: "New project" }).click();
  await expect(client.getByRole("heading", { name: "New project" })).toBeVisible();
  await client.getByLabel("Project name").fill(title);
  await client.getByLabel("Site address").fill("14 Test Avenue");
  await client.getByLabel("Town or city").fill("Independence Layout");
  await client.getByLabel("State").selectOption("Enugu");
  await client.getByLabel("Total budget (naira)").fill("2,000,000");
  // One digit short: the designed message, nothing sent.
  await client.getByRole("textbox", { name: "Contractor's phone" }).fill("803 000 000");
  await client.getByRole("button", { name: "Create and invite" }).click();
  await expect(
    client.getByText("That number is 1 digit short. Nigerian mobiles have 10 digits after +234."),
  ).toBeVisible();
  await shoot(client, "create-project-error");
  await client.getByRole("textbox", { name: "Contractor's phone" }).fill("803 000 0001");
  await client.getByRole("button", { name: "Create and invite" }).click();

  await expect(client).toHaveURL(/\/projects\/[0-9a-f-]{36}\/setup$/);
  projectId = /projects\/([0-9a-f-]{36})\/setup/.exec(client.url())![1]!;
  await expect(client.getByText("Project created")).toBeVisible();
  await expect(client.getByText("Contractor added")).toBeVisible();
  await expect(client.getByRole("link", { name: "Pin your site" })).toBeVisible();
  await shoot(client, "setup-tracker");
});

test("pin the site and draw the boundary, with the pin-outside error", async () => {
  await client.goto(`/projects/${projectId}/site`);
  await expect(client.getByRole("heading", { name: "Site and boundary" })).toBeVisible();
  await expect(client.getByText("Draft · editable")).toBeVisible();

  // On the map: three clicks with the Boundary tool make a shape.
  await client.getByRole("button", { name: "Boundary" }).click();
  const map = client.getByRole("region", { name: "Site map: the pin and the boundary" });
  const box = (await map.boundingBox())!;
  for (const [x, y] of [
    [0.3, 0.3],
    [0.7, 0.3],
    [0.5, 0.7],
  ] as const) {
    await client.mouse.click(box.x + box.width * x, box.y + box.height * y);
  }
  await expect(client.getByText("3 corners so far.")).toBeVisible();
  await client.getByRole("button", { name: "Undo" }).click();
  await expect(client.getByText("2 corners so far.")).toBeVisible();

  // Without the map: coordinates, a square around them, then a pin outside it.
  await client.getByText("Can't use the map?").click();
  await client.getByLabel("Latitude").fill("6.4483");
  await client.getByLabel("Longitude").fill("7.5139");
  await client.getByRole("button", { name: "Set the pin here" }).click();
  await client.getByRole("button", { name: /Square boundary around the pin/ }).click();
  await expect(client.getByText("4 corners so far.")).toBeVisible();
  await client.getByLabel("Latitude").fill("6.4600");
  await client.getByRole("button", { name: "Set the pin here" }).click();
  await client.getByRole("button", { name: "Save site" }).click();
  await expect(client.getByText("The pin is outside the boundary")).toBeVisible();
  await expect(client.getByText("Can’t save")).toBeVisible();
  await shoot(client, "site-pin-outside", [1280]);

  await client.getByLabel("Latitude").fill("6.4483");
  await client.getByRole("button", { name: "Set the pin here" }).click();
  await client.getByRole("button", { name: "Save site" }).click();
  await expect(client.getByText("Saved · editable until approval")).toBeVisible();
  await expect(client.getByText("Inside the boundary")).toBeVisible();
  await shoot(client, "site-saved");
});

test("review the BoQ, check it, and give the final approval", async ({ browser }) => {
  // The contractor prices the work (above the ₦2,000,000 budget) and approves; ops approves.
  const contractor = await openSignedIn(browser, test.info().project.use.baseURL, CONTRACTOR);
  await as(contractor, "put", `/api/v1/projects/${projectId}/boq`, {
    milestones: [
      {
        name: "Foundation",
        items: [
          { description: "Cement, 50 kg bag", unit: "bag", quantity: "120", unit_price_minor: 1_150_000 },
          {
            description: "Labour, foundation",
            unit: "lump sum",
            quantity: "1",
            unit_price_minor: 60_000_000,
          },
        ],
      },
      {
        name: "Roofing",
        items: [
          { description: "Roofing sheets", unit: "sheet", quantity: "80", unit_price_minor: 1_280_000 },
        ],
      },
    ],
  });
  await as(contractor, "post", `/api/v1/projects/${projectId}/boq/approve`);
  await saveSession(contractor, CONTRACTOR);
  const ops = await openSignedIn(browser, test.info().project.use.baseURL, OPS);
  await as(ops, "post", `/api/v1/projects/${projectId}/boq/approve`);
  await saveSession(ops, OPS);

  await client.goto(`/projects/${projectId}/boq`);
  await expect(client.getByText("This BoQ is above your budget")).toBeVisible();
  await expect(client.getByRole("table", { name: "Milestones" })).toContainText("Foundation");
  await expect(client.getByText("Approvals 2 of 3")).toBeVisible();
  await expect(client.getByText(/Your approval is the last one/)).toBeVisible();
  await shoot(client, "boq-review");

  // The quote check, with the model's answer given here (the comparison is the backend's plain code).
  await client.route("**/api/v1/quotes/check", (route) =>
    route.fulfill({
      json: {
        run_id: randomUUID(),
        currency: "NGN",
        threshold_percent: 15,
        flagged_count: 1,
        quote_total_minor: 300_400_000,
        lines: [
          {
            item: "Roofing sheets",
            unit: "sheet",
            quantity: "80",
            unit_price_minor: 1_280_000,
            line_total_minor: 102_400_000,
            flag: "within_index",
            index_item: "Roofing sheet",
            index_unit: "sheet",
            index_price_minor: 1_250_000,
            percent_above_index: "2.4",
            index_stale: false,
          },
          {
            item: "Cement, 50 kg bag",
            unit: "bag",
            quantity: "120",
            unit_price_minor: 1_150_000,
            line_total_minor: 138_000_000,
            flag: "over_index",
            index_item: "Cement",
            index_unit: "bag",
            index_price_minor: 980_000,
            percent_above_index: "17.3",
            index_stale: false,
          },
          {
            item: "Labour, foundation",
            unit: "lump sum",
            quantity: "1",
            unit_price_minor: 60_000_000,
            line_total_minor: 60_000_000,
            flag: "not_in_index",
            index_item: null,
            index_unit: null,
            index_price_minor: null,
            percent_above_index: null,
            index_stale: null,
          },
        ],
      },
    }),
  );
  await client.getByRole("link", { name: "Quote check" }).click();
  await expect(client.getByText("The submitted BoQ")).toBeVisible();
  await client.getByRole("button", { name: "Run the check" }).click();
  const rows = client.getByRole("table", { name: "Checked lines, flagged first" }).getByRole("row");
  await expect(rows.nth(1)).toContainText("Cement, 50 kg bag");
  await expect(rows.nth(1)).toContainText("Above index");
  await expect(client.getByText("₦204,000", { exact: true })).toBeVisible(); // (11,500 − 9,800) × 120
  await shoot(client, "quote-check");
  await client.getByRole("radio", { name: "Price index" }).click();
  await expect(client.getByText(/No supplier prices yet|Price index/).first()).toBeVisible();

  // The final approval: the project becomes active and the site locks.
  await client.goto(`/projects/${projectId}/boq`);
  await client.getByRole("button", { name: "Approve BoQ" }).click();
  await client.getByRole("alertdialog").getByRole("button", { name: "Approve BoQ" }).click();
  await expect(client.getByText("Your project is active")).toBeVisible();
  await shoot(client, "boq-approved", [1280]);
  await client.goto(`/projects/${projectId}/site`);
  await expect(client.getByText("This site is locked")).toBeVisible();
  await expect(client.getByRole("button", { name: "Save site" })).toHaveCount(0);
});
