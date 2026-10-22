import { randomUUID } from "node:crypto";

import { expect, test, type Page } from "@playwright/test";

import { axeViolations, latestCode, openSignedIn, saveSession } from "./helpers";

// W5b against the local stack: a new client goes through consent, their details and location; a new contractor
// (invited by a client) through consent, details and the payout account; the seeded contractor's home shows
// "Getting ready" on a draft project. Locally Paystack isn't set up (503), so the bank list, the account
// lookup and the save are answered in the browser with the backend's response shapes.
//   IBH_STACK=1 IBH_STACK_SEEDED=1 bun run e2e e2e/stack/onboarding.spec.ts

test.skip(!process.env.IBH_STACK, "needs the local Docker Compose stack (IBH_STACK=1)");
test.describe.configure({ mode: "serial", timeout: 120_000 });

const CLIENT = "adaeze.client@example.com";
const SEEDED_CONTRACTOR = "+2348030000001";

async function shoot(page: Page, name: string) {
  for (const width of [1280, 390]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 });
    await page.screenshot({ path: test.info().outputPath(`${name}-${width}.png`), fullPage: true });
    expect(await axeViolations(page), `${name} at ${width}`).toEqual([]);
  }
  await page.setViewportSize({ width: 1280, height: 900 });
}

async function signUp(page: Page, identifier: string) {
  await page.goto("/sign-in");
  if (identifier.startsWith("+")) {
    await page.getByRole("textbox", { name: "Phone number" }).fill(identifier);
    await page.getByLabel("SMS").check();
  } else {
    await page.getByRole("radio", { name: "Email" }).click();
    await page.getByLabel("Email address").fill(identifier);
  }
  await page.getByRole("button", { name: "Send code" }).click();
  await expect(page.getByRole("heading", { name: "Enter your code" })).toBeVisible();
  await page.getByLabel("Digit 1 of 6").fill(latestCode(identifier));
  await page.getByRole("button", { name: "Verify" }).click();
  await expect(page).toHaveURL(/\/welcome$/);
}

async function consent(page: Page) {
  await expect(page.getByRole("heading", { name: "Your data, your consent" })).toBeVisible();
  const agree = page.getByRole("button", { name: "Agree and continue" });
  await expect(agree).toBeDisabled();
  await page.getByLabel(/I agree to the Terms of use/).check();
  await expect(agree).toBeDisabled();
  await page.getByLabel(/I consent to iBackHome processing my personal data/).check();
  await agree.click();
}

test("a new client: consent, details, location, then their portal", async ({ browser }) => {
  const page = await (await browser.newContext({ baseURL: test.info().project.use.baseURL })).newPage();
  const email = `e2e-onboard-${Date.now()}@example.com`;
  await signUp(page, email);
  await shoot(page, "consent");
  await consent(page);

  await expect(page.getByRole("heading", { name: "Tell us about you" })).toBeVisible();
  await expect(page.getByText(email)).toBeVisible();
  await page.getByRole("button", { name: "Continue" }).click();
  await expect(page.getByText("Enter your full name.")).toBeVisible();
  await page.getByLabel("Full name").fill("Test Client");
  await shoot(page, "client-details");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("heading", { name: "Where you are" })).toBeVisible();
  await page.getByLabel("Country you live in").selectOption("GB");
  await page.getByLabel("Time zone").selectOption("Europe/London");
  await shoot(page, "client-location");
  await page.getByRole("button", { name: "Finish" }).click();
  await expect(page).toHaveURL(/\/projects$/);

  // Saved: /me has the details, and /welcome sends them straight on.
  const me = (await (await page.request.get("/api/v1/me")).json()) as Record<string, unknown>;
  expect(me).toMatchObject({
    full_name: "Test Client",
    country: "GB",
    timezone: "Europe/London",
    consent_required: false,
  });
  await page.goto("/welcome");
  await expect(page).toHaveURL(/\/projects$/);
});

test("a new contractor: consent, details and the payout account (Paystack answered here)", async ({
  browser,
}) => {
  // A client invites a new contractor by phone (POST /projects with contractor_phone).
  const client = await openSignedIn(browser, test.info().project.use.baseURL, CLIENT);
  const phone = `+23480${String(Date.now()).slice(-8)}`;
  const created = await client.request.post("/api/v1/projects", {
    headers: { Origin: new URL(client.url()).origin, "Idempotency-Key": randomUUID() },
    data: {
      title: `Onboarding test ${Date.now()}`,
      address: "Dev site, Enugu",
      currency: "NGN",
      budget_minor: 100_000_000,
      contractor_phone: phone,
    },
  });
  expect(created.status()).toBe(201);
  await saveSession(client, CLIENT);

  const page = await (await browser.newContext({ baseURL: test.info().project.use.baseURL })).newPage();
  const account = { bank_code: "011", bank_name: "First Bank of Nigeria", account_name: "TEST CONTRACTOR" };
  await page.route("**/api/v1/banks", (route) =>
    route.fulfill({
      json: [
        { code: "011", name: "First Bank of Nigeria" },
        { code: "058", name: "Guaranty Trust Bank" },
      ],
    }),
  );
  await page.route("**/api/v1/me/payout/recipient/resolve", (route) =>
    route.fulfill({ json: { account_name: account.account_name } }),
  );
  await page.route("**/api/v1/me/payout/recipient", (route) =>
    route.request().method() === "PUT"
      ? route.fulfill({
          json: {
            ...account,
            account_number_masked: "******6789",
            currency: "NGN",
            created_at: new Date().toISOString(),
          },
        })
      : route.fallback(),
  );

  await signUp(page, phone);
  await consent(page);
  await expect(page.getByRole("heading", { name: "Your details" })).toBeVisible();
  await page.getByLabel("Full name").fill("Test Contractor");
  await page.getByRole("button", { name: "Continue" }).click();

  await expect(page.getByRole("heading", { name: "Where should we pay you?" })).toBeVisible();
  await page.getByLabel("Bank").selectOption("011");
  await page.getByLabel("Account number (NUBAN, 10 digits)").fill("0123456789");
  await expect(page.getByText("Account found")).toBeVisible();
  await expect(page.getByText("TEST CONTRACTOR")).toBeVisible();
  await shoot(page, "contractor-payout");
  await page.getByRole("button", { name: "Save payout account" }).click();

  await expect(page.getByRole("heading", { name: "Payout account saved" })).toBeVisible();
  await expect(page.getByText("******6789 · TEST CONTRACTOR")).toBeVisible();
  await expect(page.getByText("Ready for payouts")).toBeVisible();
  await expect(page.getByText("0123456789")).toHaveCount(0);
  await shoot(page, "contractor-payout-saved");
  // The name was the contractor's own, saved for real.
  const me = (await (await page.request.get("/api/v1/me")).json()) as { full_name: string };
  expect(me.full_name).toBe("Test Contractor");
});

test("the seeded contractor's home shows Getting ready on a draft project", async ({ browser }) => {
  const client = await openSignedIn(browser, test.info().project.use.baseURL, CLIENT);
  const title = `Draft for getting ready ${Date.now()}`;
  const created = await client.request.post("/api/v1/projects", {
    headers: { Origin: new URL(client.url()).origin, "Idempotency-Key": randomUUID() },
    data: {
      title,
      address: "Dev site, Enugu",
      currency: "NGN",
      budget_minor: 100_000_000,
      contractor_phone: SEEDED_CONTRACTOR,
    },
  });
  expect(created.status()).toBe(201);
  await saveSession(client, CLIENT);

  const page = await openSignedIn(browser, test.info().project.use.baseURL, SEEDED_CONTRACTOR);
  await page.goto("/c");
  const card = page.getByRole("listitem").filter({ has: page.getByRole("heading", { name: title }) });
  await expect(card.getByText("Getting ready", { exact: true })).toBeVisible();
  await expect(card.getByText("Profile: done")).toBeAttached();
  await expect(card.getByText("Payout account: done")).toBeAttached();
  await expect(card.getByText("Bill of quantities: not yet")).toBeAttached();
  await page.screenshot({
    path: test.info().outputPath("contractor-getting-ready-1280.png"),
    fullPage: true,
  });
  expect(await axeViolations(page)).toEqual([]);
  await saveSession(page, SEEDED_CONTRACTOR);
});
