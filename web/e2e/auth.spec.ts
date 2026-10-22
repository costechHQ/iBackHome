import { expect, test } from "@playwright/test";

// No backend needed: these check routing, caching and the sign-in form itself. Signing in against the real API
// is covered with the seed driver in W4.

test("each portal sends a signed-out visitor to sign-in and back afterwards", async ({ page }) => {
  for (const path of ["/projects", "/c/projects", "/ops"]) {
    await page.goto(path);
    await expect(page).toHaveURL(`/sign-in?next=${encodeURIComponent(path)}`);
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
  for (const path of ["/projects", "/sign-in", "/api/v1/me"]) {
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
  await expect(page.getByLabel("Phone number")).toBeVisible();
  await page.getByLabel("Email").check();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await expect(page.getByText("The code arrives by email.")).toBeVisible();
});
