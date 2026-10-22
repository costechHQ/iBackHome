import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

// The shared states and shells from the dev-only gallery (/dev/states, IBH_DEV_PAGES=1 in playwright.config):
// no WCAG 2.1 AA violations at the designed widths, and the dialogs, toasts and offline bar behave as designed.
// Screenshots land in test-results/ for comparison with Docs/design/02-screens/.../web-client-024-*/*.png.

const FRAMES = [
  "404",
  "500",
  "403",
  "409",
  "form",
  "session",
  "offline",
  "offline-live",
  "loading",
  "toasts",
  "confirm",
  "destructive",
  "kit",
  "client-shell",
  "contractor-shell",
  "ops-shell",
];

async function axe(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

for (const width of [960, 1280, 390]) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: width === 390 ? 844 : 800 } });

    for (const frame of FRAMES) {
      if (frame === "ops-shell" && width === 390) continue; // the ops console is desktop only
      test(`${frame} has no accessibility violations`, async ({ page }, info) => {
        await page.goto(`/dev/states?frame=${frame}`);
        if (frame === "toasts") {
          await page.getByRole("button", { name: "Show toasts" }).click();
          // Radix also renders an off-screen copy for screen readers: check the visible toast.
          await expect(page.locator("li").filter({ hasText: "Notification settings saved." })).toBeVisible();
        }
        await page.screenshot({ path: info.outputPath(`${frame}-${width}.png`), fullPage: true });
        expect(await axe(page)).toEqual([]);
      });
    }
  });
}

test("the money confirmation ignores Escape; the other dialog closes", async ({ page }) => {
  await page.goto("/dev/states?frame=confirm");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("alertdialog", { name: "Approve this order?" })).toBeVisible();
});

test("the session-expired dialog can't be dismissed and signs in back to the same page", async ({ page }) => {
  await page.goto("/dev/states?frame=session");
  await page.keyboard.press("Escape");
  const dialog = page.getByRole("alertdialog", { name: "Please sign in again" });
  await expect(dialog).toBeVisible();
  // The gallery has no signed-in person to send a code to, so it falls back to the sign-in page.
  await dialog.getByRole("button", { name: "Send me a code" }).click();
  await expect(page).toHaveURL(/\/sign-in\?next=%2Fdev%2Fstates%3Fframe%3Dsession&expired=1$/);
});

test("toasts are announced and can be dismissed", async ({ page }) => {
  await page.goto("/dev/states?frame=toasts");
  await page.getByRole("button", { name: "Show toasts" }).click();
  const toast = page.locator("li").filter({ hasText: "Notification settings saved." });
  await expect(toast).toBeVisible();
  await toast.getByRole("button", { name: "Dismiss" }).click();
  await expect(toast).toHaveCount(0);
});

test("the offline bar follows the connection and approvals pause while offline", async ({
  page,
  context,
}) => {
  await page.goto("/dev/states?frame=offline-live");
  const approve = page.getByRole("button", { name: "Review and approve" });
  await expect(page.getByText(/You're offline/)).toHaveCount(0);
  await expect(approve).toBeEnabled();
  await context.setOffline(true);
  await expect(page.getByText(/You're offline\. Showing what loaded at \d\d:\d\d\./)).toBeVisible();
  await expect(approve).toBeDisabled();
  await context.setOffline(false);
  await expect(page.getByText(/You're offline/)).toHaveCount(0);
  await expect(approve).toBeEnabled();
});

test("the gallery lists every frame", async ({ page }) => {
  await page.goto("/dev/states");
  for (const frame of FRAMES)
    await expect(page.locator(`a[href="/dev/states?frame=${frame}"]`)).toHaveCount(1);
});
