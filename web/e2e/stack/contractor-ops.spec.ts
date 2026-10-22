import { expect, test, type Page } from "@playwright/test";

import { axeViolations, openSignedIn, saveSession } from "./helpers";

// W3 against the local stack, after the seed driver (web/README.md, "Seed driver"): the contractor's dashboard,
// milestones and the sent-back screen, then the ops dispute queue and the two-approver resolution.
// It changes data: the contractor claims the sent-back milestone again, and two ops users resolve the open
// dispute for release. Put them back with the driver (--to sent-back, --to disputed) before running it again.
//   IBH_STACK=1 bun run e2e e2e/stack/contractor-ops.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 120_000 });

const CONTRACTOR = "+2348030000001";
const OPS_1 = "ops@example.com";
const OPS_2 = "ops2@example.com";

type Milestone = {
  id: string;
  name: string;
  status: string;
  project_id: string;
  latest_verification?: { decision: string } | null;
};

async function milestonesOf(page: Page): Promise<Milestone[]> {
  const projects = (await (await page.request.get("/api/v1/projects")).json()) as { items: { id: string }[] };
  const all: Milestone[] = [];
  for (const p of projects.items) {
    all.push(
      ...((await (await page.request.get(`/api/v1/projects/${p.id}/milestones`)).json()) as Milestone[]),
    );
  }
  return all;
}

async function shoot(page: Page, path: string, name: string, widths: readonly number[]) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.goto(path);
    await page.waitForLoadState("networkidle");
    await page.screenshot({ path: test.info().outputPath(`${name}-${width}.png`), fullPage: true });
    expect(await axeViolations(page), `${name} at ${width}`).toEqual([]);
  }
}

test.describe("contractor", () => {
  let page: Page;
  let sentBack: Milestone | undefined;

  test.beforeAll(async ({ browser }) => {
    page = await openSignedIn(browser, test.info().project.use.baseURL, CONTRACTOR);
    sentBack = (await milestonesOf(page)).find(
      (m) => m.status === "funded" && m.latest_verification?.decision === "rejected",
    );
  });
  test.afterAll(async () => {
    if (page) await saveSession(page, CONTRACTOR);
  });

  test("dashboard and milestones", async () => {
    await shoot(page, "/c", "contractor-home", [1280, 390]);
    if (sentBack) await expect(page.getByRole("link", { name: "See what to fix" }).first()).toBeVisible();
    const projects = (await (await page.request.get("/api/v1/projects")).json()) as {
      items: { id: string }[];
    };
    for (const [i, p] of projects.items.entries()) {
      await shoot(page, `/c/projects/${p.id}/milestones`, `contractor-milestones-${i + 1}`, [1280]);
    }
  });

  test("sent back, then claimed again", async () => {
    test.skip(!sentBack, "no milestone sent back: run the driver with --to sent-back");
    const path = `/c/projects/${sentBack!.project_id}/milestones/${sentBack!.id}`;
    await shoot(page, path, "contractor-sent-back", [1280, 390]);
    await page.setViewportSize({ width: 1280, height: 900 });
    await expect(page.getByText("Sent back by the supervisor")).toBeVisible();
    await expect(page.getByText("still held for you")).toBeVisible();
    await page.getByRole("button", { name: `Claim ${sentBack!.name} again` }).click();
    await page.getByRole("alertdialog").getByRole("button", { name: "Claim milestone" }).click();
    await expect(page.getByText("This milestone hasn't been sent back.")).toBeVisible();
    await page.goto(`/c/projects/${sentBack!.project_id}/milestones`);
    await expect(page.getByText("Waiting for the supervisor").first()).toBeVisible();
  });
});

test.describe("ops: two-approver dispute resolution", () => {
  let first: Page;
  let second: Page;
  let disputeId: string | undefined;
  let proposed = false;

  test.beforeAll(async ({ browser }) => {
    const baseURL = test.info().project.use.baseURL;
    first = await openSignedIn(browser, baseURL, OPS_1);
    second = await openSignedIn(browser, baseURL, OPS_2);
    const queue = (await (await first.request.get("/api/v1/ops/queue")).json()) as {
      disputes: { dispute_id: string; proposed_by: string | null }[];
    };
    const me = (await (await first.request.get("/api/v1/me")).json()) as { id: string };
    // A dispute nobody has proposed yet, or one ops 1 proposed in an earlier run that stopped half way.
    const open = queue.disputes.find((d) => !d.proposed_by || d.proposed_by === me.id);
    disputeId = open?.dispute_id;
    proposed = Boolean(open?.proposed_by);
  });
  test.afterAll(async () => {
    if (first) await saveSession(first, OPS_1);
    if (second) await saveSession(second, OPS_2);
  });

  test("the queue", async () => {
    await shoot(first, "/ops/disputes", "ops-disputes", [1440]);
    // A table when disputes are open (CI puts one there with the driver), else the empty state.
    await expect(
      first.getByRole("table", { name: "Open disputes" }).or(first.getByText("No open disputes")),
    ).toBeVisible();
  });

  test("one proposes, the same person can't confirm, a second one does", async () => {
    test.skip(!disputeId, "no open dispute without a proposal: run the driver with --to disputed");
    const path = `/ops/disputes/${disputeId}`;
    await shoot(first, path, proposed ? "ops-dispute-awaiting" : "ops-dispute-propose", [1440]);
    if (!proposed) {
      // Step 1: a note is required, then the proposal is recorded and nothing moves yet.
      await first.getByRole("button", { name: "Propose release" }).click();
      await expect(first.getByText("Write a note.")).toBeVisible();
      await first.getByLabel("Your note (required)").fill("Checked the evidence: the work is done.");
      await first.getByRole("button", { name: "Propose release" }).click();
      await expect(first.getByText("Waiting for a second approver")).toBeVisible();
      await first.screenshot({
        path: test.info().outputPath("ops-dispute-awaiting-1440.png"),
        fullPage: true,
      });
    }

    // The same person confirming is refused by the backend (the screen offers no button for it).
    const own = await first.request.post(`/api/v1/disputes/${disputeId}/resolve`, {
      data: { outcome: "release", notes: "Confirming my own proposal" },
      headers: { Origin: new URL(first.url()).origin },
    });
    expect(own.status()).toBe(409);
    expect(((await own.json()) as { error: { code: string } }).error.code).toBe("second_approval_required");

    // Step 2: a different ops person sees the proposal and its note, and confirms the same outcome.
    await shoot(second, path, "ops-dispute-second-approver", [1440]);
    await expect(second.getByText("Step 2 · Second approver (you)")).toBeVisible();
    await expect(
      second.getByText("“Checked the evidence: the work is done.”", { exact: true }),
    ).toBeVisible();
    await second.getByLabel("Your note (required)").fill("Agree: the evidence shows it finished.");
    await second.getByRole("button", { name: "Approve release" }).click();
    await expect(second.getByText("Resolved: release", { exact: true })).toBeVisible();
    await second.screenshot({
      path: test.info().outputPath("ops-dispute-resolved-1440.png"),
      fullPage: true,
    });
  });
});
