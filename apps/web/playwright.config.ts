import { defineConfig, devices } from "@playwright/test";

const frontendUrl = process.env.PROOFPILOT_E2E_FRONTEND_URL ?? "http://127.0.0.1:3013";
const frontendPort = new URL(frontendUrl).port || "80";

export default defineConfig({
  expect: {
    timeout: 10_000,
  },
  fullyParallel: false,
  reporter: "list",
  testDir: "./e2e",
  timeout: 30_000,
  use: {
    baseURL: frontendUrl,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    ...devices["Desktop Chrome"],
  },
  webServer: {
    command: `pnpm build && pnpm exec next start --hostname 127.0.0.1 --port ${frontendPort}`,
    reuseExistingServer: false,
    timeout: 120_000,
    url: frontendUrl,
  },
});
