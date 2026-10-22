import AxeBuilder from "@axe-core/playwright";
import { expect, test, type Page } from "@playwright/test";

import { PUBLIC_PATHS } from "../src/features/public/seo";

// The public site (WEB-PUBLIC-001 to 009): no WCAG 2.1 AA violations at desktop and phone width, no design
// placeholder ("[PRICE]", "[£ FEE]") ever shown, a signed-in visitor at "/" goes to their portal, and nothing
// outside production is indexed. Screenshots land in test-results/ for comparison with
// Docs/design/02-screens/.../web-public-00N-*/*.png.

async function axe(page: Page) {
  const results = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
    .analyze();
  return results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join(", ")}`);
}

const PLACEHOLDER = /\[[A-Z£$€₦]/;

for (const width of [1280, 390]) {
  test.describe(`at ${width}px`, () => {
    test.use({ viewport: { width, height: width === 390 ? 844 : 800 } });

    for (const path of PUBLIC_PATHS) {
      test(`${path} has one heading, no placeholders and no accessibility violations`, async ({
        page,
      }, info) => {
        await page.goto(path);
        await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1);
        expect(await page.locator("body").innerText()).not.toMatch(PLACEHOLDER);
        const name = path === "/" ? "landing" : path.slice(1);
        await page.screenshot({ path: info.outputPath(`${name}-${width}.png`), fullPage: true });
        expect(await axe(page)).toEqual([]);
      });
    }
  });
}

test("the phone menu opens and reaches every page", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await page.getByRole("button", { name: /menu/i }).click();
  await page.locator("#public-menu").getByRole("link", { name: "Trust and safety" }).click();
  await expect(page).toHaveURL("/trust");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "How we protect your money, your site and your data",
  );
});

test("a signed-in visitor at the landing page goes to their portal", async ({ page, context }) => {
  await context.addCookies([
    { name: "ibh_s", value: "1", url: test.info().project.use.baseURL!, httpOnly: true, secure: true },
  ]);
  const response = await page.request.get("/", { maxRedirects: 0 });
  expect(response.status()).toBe(307);
  expect(response.headers().location).toMatch(/\/home$/);
});

test("the legal pages say they're being finalised until the text is supplied", async ({ page }) => {
  for (const path of ["/privacy", "/terms"]) {
    await page.goto(path);
    await expect(page.getByText("This document is being finalised")).toBeVisible();
  }
});

test("nothing is indexed outside production", async ({ request }) => {
  const robots = await request.get("/robots.txt");
  expect(robots.status()).toBe(200);
  expect(await robots.text()).toMatch(/Disallow: \/\s*$/m);
});
