import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  workers: 4,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  use: {
    baseURL: process.env.AEGIS_E2E_BASE_URL ?? "http://127.0.0.1:3104",
    trace: "retain-on-failure",
    launchOptions: {
      executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE,
    },
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  webServer:
    process.env.AEGIS_E2E_EXTERNAL_SERVER === "1"
      ? undefined
      : {
          command:
            "node node_modules/next/dist/bin/next dev --hostname 127.0.0.1 --port 3104",
          url: "http://127.0.0.1:3104",
          reuseExistingServer: false,
          timeout: 120000,
          env: { NEXT_PUBLIC_DATA_MODE: "mock" },
        },
});
