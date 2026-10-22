import { defineConfig, devices } from "@playwright/test";

// Not 3000: the Docker Compose `web` service uses it, and a test must never run against that build by mistake.
const port = Number(process.env.PORT ?? 3010);
const baseURL = process.env.PLAYWRIGHT_BASE_URL ?? `http://127.0.0.1:${port}`;

// Runs against the production build (`next build` first, then `next start`), as in CI.
// Set PLAYWRIGHT_BASE_URL to test a running stack instead (local Compose or staging).
export default defineConfig({
  testDir: "./e2e",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  // The stack tests share one database and change it (claims, approvals, resolutions): one at a time.
  workers: process.env.IBH_STACK ? 1 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: { baseURL, trace: "retain-on-failure" },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // Locally, evidence URLs name the Docker storage host; map it so images load (no hosts-file change).
        launchOptions: { args: ["--host-resolver-rules=MAP storage 127.0.0.1"] },
      },
    },
  ],
  webServer: process.env.PLAYWRIGHT_BASE_URL
    ? undefined
    : [
        {
          command: `bun run start -- --port ${port}`,
          // IBH_DEV_PAGES turns on the dev-only states gallery for the axe and screenshot tests (e2e/states.spec.ts).
          env: {
            API_INTERNAL_URL: process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000",
            IBH_DEV_PAGES: "1",
            IBH_MOCKS: "all",
          },
          url: `${baseURL}/api/healthz`,
          reuseExistingServer: false,
          timeout: 60_000,
        },
        // The same build as production runs it: no mocks, no dev pages (e2e/stack/gate-guards.spec.ts).
        {
          command: `bun run start -- --port ${port + 1}`,
          env: { API_INTERNAL_URL: process.env.API_INTERNAL_URL ?? "http://127.0.0.1:8000" },
          url: `http://127.0.0.1:${port + 1}/api/healthz`,
          reuseExistingServer: false,
          timeout: 60_000,
        },
      ],
});
