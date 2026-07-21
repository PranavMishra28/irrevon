import { defineConfig } from "@playwright/test";

// Tests run against the built output (astro preview over dist/). `pnpm build`
// first; the webServer block reuses an already-running preview.
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:4977",
  },
  webServer: {
    command: "pnpm preview --port 4977",
    port: 4977,
    reuseExistingServer: true,
  },
  projects: [
    { name: "checks", testMatch: /(a11y|links|budget)\.spec\.ts/ },
    { name: "shots", testMatch: /shots\.spec\.ts/ },
  ],
});
