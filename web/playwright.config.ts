import { defineConfig, devices } from "@playwright/test";

/**
 * - e2e: workflows + a11y against the built review app. 1 retry max;
 *   a pass-on-retry is reported, never silently absorbed.
 * - vrt: pixel baselines. Authoritative only inside the pinned Linux
 *   container (make web-vrt); a bare local run skips the project.
 *   Zero retries: a flaky screenshot means determinism leaked.
 */
const IS_VRT_ENV = process.env.DETENT_VRT_CONTAINER === "1";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:5199",
    trace: "on-first-retry",
  },
  expect: {
    toHaveScreenshot: {
      maxDiffPixels: 0,
      animations: "disabled",
      caret: "hide",
      scale: "css",
    },
  },
  // Resolves against the vrt project's testDir (e2e/visual); baselines are
  // Linux-only, generated inside the pinned container (see web/README.md).
  snapshotPathTemplate: "{testDir}/__baselines__/{testFileName}/{arg}-linux{ext}",
  projects: [
    {
      name: "e2e",
      testDir: "./e2e/workflows",
      retries: 1,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "a11y",
      testDir: "./e2e/a11y",
      retries: 0,
      use: { ...devices["Desktop Chrome"] },
    },
    {
      name: "vrt",
      testDir: "./e2e/visual",
      retries: 0,
      // Outside the pinned container nothing matches; VRT is container-only.
      grep: IS_VRT_ENV ? /.*/ : /$^/,
      use: {
        ...devices["Desktop Chrome"],
        contextOptions: { reducedMotion: "reduce" },
      },
    },
  ],
  webServer: {
    command: "pnpm run build:review && pnpm exec vite preview --port 5199 --strictPort",
    url: "http://localhost:5199",
    reuseExistingServer: !process.env.CI && !IS_VRT_ENV,
    timeout: 120_000,
  },
});
