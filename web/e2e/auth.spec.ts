import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

// No backend needed: these check routing, caching and the sign-in form itself. Signing in against the real API
// is covered by the stack tests (e2e/stack, IBH_STACK=1).

test("each portal sends a signed-out visitor to sign-in and back afterwards", async ({ page }) => {
  for (const path of ["/projects", "/c", "/c/projects/x/milestones", "/ops", "/ops/disputes/x", "/welcome"]) {
    await page.goto(path);
    const signIn = path.startsWith("/ops") ? "/ops/sign-in" : "/sign-in";
    await expect(page).toHaveURL(`${signIn}?next=${encodeURIComponent(path)}`);
  }
});

test("a visitor whose session cookie is left but whose token is gone goes through refresh", async ({
  page,
  context,
}) => {
  await context.addCookies([
    { name: "ibh_s", value: "1", url: test.info().project.use.baseURL!, httpOnly: true, secure: true },
  ]);
  const response = await page.request.get("/projects", { maxRedirects: 0 });
  expect(response.status()).toBe(307);
  expect(response.headers().location).toContain("/api/session/refresh?next=%2Fprojects");
});

test("portal pages, sign-in and the API proxy are never cacheable", async ({ request }) => {
  for (const path of [
    "/projects",
    "/c",
    "/c/projects/x/milestones",
    "/ops",
    "/ops/disputes",
    "/ops/disputes/x",
    "/welcome",
    "/sign-in",
    "/api/v1/me",
  ]) {
    const res = await request.get(path, { maxRedirects: 0 });
    expect(res.headers()["cache-control"], path).toContain("no-store");
  }
});

test("the API proxy refuses the token routes and cross-site writes", async ({ request }) => {
  expect((await request.post("/api/v1/auth/refresh", { data: {} })).status()).toBe(404);
  const csrf = await request.post("/api/v1/projects", {
    data: {},
    headers: { origin: "https://evil.example" },
  });
  expect(csrf.status()).toBe(403);
});

test("the sign-in form has labelled fields and switches to email", async ({ page }) => {
  await page.goto("/sign-in");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Sign in or create an account");
  await expect(page.getByRole("textbox", { name: "Phone number" })).toBeVisible();
  await page.getByRole("radio", { name: "Email" }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByText("The code arrives by email.")).toBeVisible();
});

test("the country picker searches by name or code, common countries first, keyboard only", async ({
  page,
}) => {
  await page.goto("/sign-in");
  const picker = page.getByRole("button", { name: /Phone number/ });
  await expect(picker).toContainText("GB +44");
  await picker.click();
  const options = page.getByRole("option");
  await expect(options.first()).toContainText("United Kingdom");
  await expect(options.nth(5)).toContainText("Nigeria");
  await page.keyboard.type("234");
  await expect(options).toHaveCount(1);
  await page.keyboard.press("Enter");
  await expect(picker).toContainText("NG +234");
  await expect(picker).toBeFocused();
  await picker.click();
  await page.keyboard.press("Escape");
  await expect(page.getByRole("listbox")).toHaveCount(0);
});

const AUTH_PAGES = [
  ["sign-in", "/sign-in"],
  ["ops-sign-in", "/ops/sign-in"],
  ["signed-out", "/signed-out"],
] as const;

for (const [name, path] of AUTH_PAGES) {
  test(`${name} has no accessibility violations at 1280 and 390 px`, async ({ page }, info) => {
    for (const width of [1280, 390]) {
      await page.setViewportSize({ width, height: width === 390 ? 844 : 800 });
      await page.goto(path);
      await page.screenshot({ path: info.outputPath(`${name}-${width}.png`), fullPage: true });
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa"])
        .analyze();
      expect(
        results.violations.map((v) => v.id),
        `${path} at ${width}`,
      ).toEqual([]);
    }
  });
}

test("the ops sign-in is for staff, by work email", async ({ page }) => {
  await page.goto("/ops/sign-in");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Staff sign-in");
  await expect(page.getByLabel("Work email")).toBeVisible();
  await expect(page.getByRole("button", { name: "Email me a code" })).toBeDisabled();
  await expect(page.getByRole("textbox", { name: "Phone number" })).toHaveCount(0);
});

// The backend's answers to POST /auth/otp/request when sending fails, in its error shape. Locally every
// channel is "sent" to the API log, so these states are checked by answering for the backend here.
function answerOtpRequest(status: number, code: string, headers: Record<string, string> = {}) {
  return {
    status,
    headers: { "content-type": "application/json", ...headers },
    body: JSON.stringify({ error: { code, message: code } }),
  };
}

test("WhatsApp unavailable (503): the designed state marks it and offers SMS", async ({ page }, info) => {
  await page.route("**/api/v1/auth/otp/request", (route) =>
    route.fulfill(answerOtpRequest(503, "notifications_not_configured")),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/sign-in");
  await page.getByRole("textbox", { name: "Phone number" }).fill("7911 123456");
  await page.getByLabel("WhatsApp").check();
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByText("WhatsApp codes aren’t available right now.")).toBeVisible();
  await expect(page.getByText("Unavailable")).toBeVisible();
  await expect(page.getByLabel("WhatsApp")).toBeDisabled();
  await expect(page.getByLabel("SMS")).toBeChecked();
  await page.screenshot({ path: info.outputPath("sign-in-503-390.png"), fullPage: true });
});

test("too many codes (429): waits for Retry-After before asking again", async ({ page }) => {
  await page.route("**/api/v1/auth/otp/request", (route) =>
    route.fulfill(answerOtpRequest(429, "rate_limited", { "retry-after": "581" })),
  );
  await page.goto("/sign-in");
  await page.getByRole("textbox", { name: "Phone number" }).fill("7911 123456");
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByText("Too many codes requested.")).toBeVisible();
  await expect(page.getByText(/wait 10 minutes/)).toBeVisible();
  await expect(page.getByRole("button", { name: /^Try again in 9:\d\d$/ })).toBeDisabled();
});

test("sending failed (502): says so and offers to try again", async ({ page }) => {
  await page.route("**/api/v1/auth/otp/request", (route) =>
    route.fulfill(answerOtpRequest(502, "notification_failed")),
  );
  await page.goto("/sign-in");
  await page.getByRole("textbox", { name: "Phone number" }).fill("7911 123456");
  await page.getByLabel("SMS").check();
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByText("We couldn’t send your code by SMS.")).toBeVisible();
  await expect(page.getByText("Try again, or choose WhatsApp or email.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" })).toBeEnabled();
});

test("the code step: countdown, resend after 30 s, and the right number masked", async ({ page }) => {
  await page.route("**/api/v1/auth/otp/request", (route) =>
    route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ status: "sent", expires_in: 300 }),
    }),
  );
  await page.goto("/sign-in");
  await page.getByRole("textbox", { name: "Phone number" }).fill("07700 900482");
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await expect(page.getByText("+44 7700 ••• 482")).toBeVisible();
  await expect(page.getByText(/Code expires in 4:5\d|Code expires in 5:00/)).toBeVisible();
  await expect(page.getByText(/Resend in 0:[23]\d/)).toBeVisible();
  await expect(page.getByRole("button", { name: "Verify" })).toBeDisabled();
  // Pasting the code fills every box.
  await page.getByLabel("Digit 1 of 6").fill("482193");
  await expect(page.getByLabel("Digit 6 of 6")).toHaveValue("3");
  await expect(page.getByRole("button", { name: "Verify" })).toBeEnabled();
  // Back keeps what was typed.
  await page.getByRole("button", { name: "Back" }).click();
  await expect(page.getByRole("textbox", { name: "Phone number" })).toHaveValue("07700 900482");
});
