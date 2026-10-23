import { expect, test, type Page } from "@playwright/test";

import { axeViolations, drive, driveApplicant, openSignedIn, saveSession } from "./helpers";

// W8b against the local stack: a new supervisor application (the driver's --applicant, who declares the
// seeded contractor as a cousin) is vetted: approve stays locked until all four checks are ticked, rejecting
// needs a reason, then ops approves. On a fresh live project (the driver's --new-project) the new supervisor is
// blocked as a relative of the contractor, and ops hands the project to the second seeded supervisor. Then ops
// books a spot check by the first one. Axe at 1440 px (the ops console is desktop only).
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/ops-supervision.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 300_000 });

const OPS = "ops@example.com";
const SUPERVISOR_1 = "Ifeoma Eze"; // the driver's new projects start with her (backend/scripts/seed.py)
const SUPERVISOR_2 = "Nnamdi Okeke";

let ops: Page;
let applicantId: string;
let projectId: string;
let projectTitle: string;

async function shoot(page: Page, name: string) {
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.waitForLoadState("networkidle");
  await page.screenshot({ path: test.info().outputPath(`${name}-1440.png`), fullPage: true });
  expect(await axeViolations(page), name).toEqual([]);
}

test.beforeAll(async ({ browser }) => {
  applicantId = driveApplicant();
  projectId = drive("--new-project", "--to", "funded").projectId;
  ops = await openSignedIn(browser, test.info().project.use.baseURL, OPS);
  projectTitle = (
    (await (await ops.request.get(`/api/v1/projects/${projectId}`)).json()) as { title: string }
  ).title;
});
test.afterAll(async () => {
  if (ops) await saveSession(ops, OPS);
});

test("vetting: approve stays locked until every check is ticked", async () => {
  await ops.goto("/ops/vetting");
  await ops.getByRole("link", { name: `Application ${applicantId.slice(0, 8)}` }).click();
  await expect(ops.getByRole("heading", { name: /supervisor application/ })).toBeVisible();
  await expect(ops.getByText("cousin", { exact: false })).toBeVisible();
  await expect(ops.getByText("Ngozi Eze, +2348031234567")).toBeVisible();
  await shoot(ops, "ops-vetting-detail");

  const approve = ops.getByRole("button", { name: "Approve applicant" });
  await expect(approve).toBeDisabled();
  await ops.getByRole("button", { name: "Reject" }).click();
  await expect(ops.getByText("Say why, so the applicant knows what to fix.")).toBeVisible();

  for (const label of [
    "Registration checked on the register",
    "NIN matched",
    "First guarantor confirmed by phone",
  ]) {
    await ops.getByLabel(label).check();
  }
  await expect(approve).toBeDisabled();
  await expect(ops.getByText("1 to go")).toBeVisible();
  await ops.getByLabel("Second guarantor confirmed by phone").check();
  await expect(approve).toBeEnabled();
  await approve.click();
  await ops.getByRole("alertdialog").getByRole("button", { name: "Approve applicant" }).click();
  await expect(ops.getByText("Approved", { exact: true })).toBeVisible();
});

test("choosing a supervisor: a relative of the contractor is blocked; another takes over", async () => {
  await ops.goto(`/ops/projects/${projectId}`);
  const table = ops.getByRole("table", { name: "Vetted supervisors" });
  await expect(table).toBeVisible();
  const relative = table.getByRole("row").filter({ hasText: "Test Applicant" }).first();
  await expect(relative.getByText("Related to contractor")).toBeVisible();
  await expect(relative.getByRole("button", { name: /Assign/ })).toHaveCount(0);
  await shoot(ops, "ops-project-supervisor");

  await table.getByRole("button", { name: `Assign ${SUPERVISOR_2}` }).click();
  const dialog = ops.getByRole("alertdialog", { name: `Assign ${SUPERVISOR_2}?` });
  await expect(dialog).toContainText(`They take over from ${SUPERVISOR_1}`);
  await dialog.getByRole("button", { name: "Assign supervisor" }).click();
  await expect(ops.getByText("Supervisor assigned")).toBeVisible();
  await expect(ops.getByText(`${SUPERVISOR_2} · `)).toBeVisible();
});

test("spot checks: book one by a supervisor who isn't the project's own", async () => {
  await ops.getByRole("link", { name: "Book one" }).click();
  await expect(ops.getByRole("heading", { name: "Spot checks" })).toBeVisible();
  await expect(ops.getByLabel("Project")).toHaveValue(projectId);
  const supervisor = ops.getByLabel("Supervisor");
  await expect(supervisor.locator("option", { hasText: SUPERVISOR_2 })).toBeDisabled();
  const eligible = supervisor.locator("option:not([disabled])", { hasText: SUPERVISOR_1 });
  await supervisor.selectOption((await eligible.getAttribute("value"))!);
  const tomorrow = new Date(Date.now() + 24 * 60 * 60_000).toISOString().slice(0, 10);
  await ops.getByLabel("Day").fill(tomorrow);
  await ops.getByLabel("Time (WAT)").fill("10:30");
  await ops.getByRole("button", { name: "Schedule spot check" }).click();
  await expect(ops.getByText("Spot check booked")).toBeVisible();
  const upcoming = ops.getByRole("listitem").filter({ hasText: projectTitle });
  await expect(upcoming.first()).toContainText(SUPERVISOR_1);
  await shoot(ops, "ops-spot-checks");

  await ops.goto(`/ops/projects/${projectId}`);
  await expect(ops.getByRole("heading", { name: "Spot checks" })).toBeVisible();
  await expect(ops.getByText("Scheduled").first()).toBeVisible();
});
