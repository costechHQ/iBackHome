import { expect, test, type Page } from "@playwright/test";

import { axeViolations, drive, openSignedIn, saveSession } from "./helpers";

// The web gate (build-order Stage 2): the milestone release journey end to end, through the screens, on a fresh
// project each run, so it repeats with no manual reset. The people the web app serves act in the browser
// (contractor claims, client approves and disputes, two ops users resolve); the steps that happen elsewhere
// (Stripe funding, the supervisor's Android captures and verification) go through the seed driver and the real
// API. Simulated escrow releases the money.
//   IBH_STACK=1 bun run e2e e2e/stack/gate.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 300_000 });

const CLIENT = "adaeze.client@example.com";
const CONTRACTOR = "+2348030000001";
const OPS_1 = "ops@example.com";
const OPS_2 = "ops2@example.com";

let client: Page;
let contractor: Page;
let ops1: Page;
let ops2: Page;
let projectId: string;

test.beforeAll(async ({ browser }) => {
  test.setTimeout(300_000);
  const baseURL = test.info().project.use.baseURL;
  client = await openSignedIn(browser, baseURL, CLIENT);
  contractor = await openSignedIn(browser, baseURL, CONTRACTOR);
  ops1 = await openSignedIn(browser, baseURL, OPS_1);
  ops2 = await openSignedIn(browser, baseURL, OPS_2);
  // A new project: BoQ approved by client, contractor and ops; milestone 1 funded by the client.
  projectId = drive("--new-project", "--to", "funded").projectId;
});
test.afterAll(async () => {
  if (client) await saveSession(client, CLIENT);
  if (contractor) await saveSession(contractor, CONTRACTOR);
  if (ops1) await saveSession(ops1, OPS_1);
  if (ops2) await saveSession(ops2, OPS_2);
});

type Milestone = { id: string; sequence: number; status: string; name: string };

async function milestone(page: Page, sequence: number): Promise<Milestone> {
  const list = (await (
    await page.request.get(`/api/v1/projects/${projectId}/milestones`)
  ).json()) as Milestone[];
  return list.find((m) => m.sequence === sequence)!;
}

async function waitFor(page: Page, sequence: number, status: string, seconds = 90) {
  await expect
    .poll(async () => (await milestone(page, sequence)).status, {
      timeout: seconds * 1000,
      intervals: [1500],
    })
    .toBe(status);
}

test("fund → capture → claim → verify → approve → release", async () => {
  const m1 = await milestone(client, 1);
  expect(m1.status).toBe("funded");

  // The contractor claims in the web app.
  await contractor.setViewportSize({ width: 1280, height: 900 });
  await contractor.goto(`/c/projects/${projectId}/milestones`);
  await contractor.getByRole("button", { name: "Claim milestone" }).click();
  await contractor.getByRole("alertdialog").getByRole("button", { name: "Claim milestone" }).click();
  await expect(contractor.getByText("Waiting for the supervisor").first()).toBeVisible();
  await waitFor(client, 1, "claimed", 10);

  // Nobody but the client can approve, and not before verification: no approve action anywhere yet.
  await client.goto(`/projects/${projectId}/milestones/${m1.id}`);
  await expect(client.getByRole("button", { name: "Approve release" })).toHaveCount(0);
  await expect(client.getByRole("link", { name: "Approve release" })).toHaveCount(0);

  // The supervisor captures signed evidence on site and verifies (Android; through the driver).
  drive("--project", projectId, "--milestone", "1", "--to", "verified");

  // The client approves on a phone in three taps.
  await client.setViewportSize({ width: 390, height: 844 });
  await client.goto(`/projects/${projectId}/milestones/${m1.id}`);
  await client.getByRole("link", { name: "Approve release" }).first().click();
  await client.getByRole("button", { name: "Approve release" }).click();
  await client.getByRole("button", { name: "Confirm and release" }).click();
  await expect(client).toHaveURL(new RegExp(`${m1.id}$`));

  // The escrow partner (simulated) releases; the client sees it, the receipt and the ledger row.
  await waitFor(client, 1, "released");
  await client.setViewportSize({ width: 1280, height: 900 });
  await client.goto(`/projects/${projectId}/milestones/${m1.id}/receipt`);
  await expect(client.getByRole("heading", { name: `${m1.name} is released` })).toBeVisible();
  expect(await axeViolations(client)).toEqual([]);
  await client.screenshot({ path: test.info().outputPath("gate-receipt-1280.png"), fullPage: true });
  await client.goto(`/projects/${projectId}/ledger`);
  await expect(client.getByText(`Release · ${m1.name}`).first()).toBeVisible();
  await client.screenshot({ path: test.info().outputPath("gate-ledger-1280.png"), fullPage: true });

  // The contractor sees it released.
  await contractor.goto(`/c/projects/${projectId}/milestones`);
  await expect(contractor.getByText(/^Released /).first()).toBeVisible();
});

test("dispute → ops 1 proposes rework → ops 2 confirms → back to funded", async () => {
  const { milestoneId } = drive("--project", projectId, "--milestone", "2", "--to", "verified");

  // The client disputes in the web app: the release pauses.
  await client.setViewportSize({ width: 1280, height: 900 });
  await client.goto(`/projects/${projectId}/milestones/${milestoneId}/dispute`);
  await client.getByRole("radio", { name: "Quality problem in the finished work" }).check();
  await client.getByLabel("Tell us more").fill("Gate test: the plaster is cracking on the east wall.");
  await client.getByRole("button", { name: "Raise dispute and pause release" }).click();
  await expect(client.getByRole("heading", { name: "Under review by iBackHome" })).toBeVisible();
  await waitFor(client, 2, "disputed", 10);
  // A dispute leaves no approve action anywhere.
  await client.goto(`/projects/${projectId}/milestones/${milestoneId}`);
  await expect(client.getByRole("button", { name: "Approve release" })).toHaveCount(0);
  await expect(client.getByRole("link", { name: "Approve release" })).toHaveCount(0);

  // Ops 1 finds it in the queue and proposes rework.
  const queue = (await (await ops1.request.get("/api/v1/ops/queue")).json()) as {
    disputes: { dispute_id: string; milestone_id: string }[];
  };
  const dispute = queue.disputes.find((d) => d.milestone_id === milestoneId)!;
  await ops1.setViewportSize({ width: 1440, height: 900 });
  await ops1.goto("/ops/disputes");
  await ops1.getByRole("link", { name: new RegExp(`^D-${dispute.dispute_id.slice(0, 8)}`) }).click();
  await ops1.getByRole("radio", { name: "Rework" }).click();
  await ops1.getByLabel("Your note (required)").fill("Gate test: the cracking needs fixing first.");
  await ops1.getByRole("button", { name: "Propose rework" }).click();
  await expect(ops1.getByText("Waiting for a second approver")).toBeVisible();
  // The proposer has no way to approve their own proposal.
  await expect(ops1.getByRole("button", { name: /^Approve/ })).toHaveCount(0);

  // Ops 2 confirms the same outcome.
  await ops2.setViewportSize({ width: 1440, height: 900 });
  await ops2.goto(`/ops/disputes/${dispute.dispute_id}`);
  await expect(ops2.getByText("Step 2 · Second approver (you)")).toBeVisible();
  expect(await axeViolations(ops2)).toEqual([]);
  await ops2.getByLabel("Your note (required)").fill("Gate test: agreed, rework.");
  await ops2.getByRole("button", { name: "Approve rework" }).click();
  await expect(ops2.getByText("Resolved: rework", { exact: true })).toBeVisible();

  // Back to funded: the money stays held and the contractor can claim again.
  await waitFor(client, 2, "funded", 10);
  await contractor.goto(`/c/projects/${projectId}/milestones`);
  await expect(contractor.getByRole("button", { name: "Claim milestone" })).toBeVisible();
});
