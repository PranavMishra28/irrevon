import { defineConfig, devices } from "@playwright/test";

/**
 * The REAL live E2E (`make web-e2e-live`): demo --keep → `irrevon serve` →
 * Playwright, against the packaged workbench the engine itself serves
 * (src/irrevon/_web, staged by `make web-build dist-stage`). Separate config
 * because the suite owns the server process (no webServer block) and targets
 * the engine-provided origin, not a Vite preview. Zero retries — a flake is
 * a bug.
 */
export default defineConfig({
  testDir: "./e2e/live-real",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  reporter: [["list"]],
  projects: [
    {
      name: "live-real",
      retries: 0,
      use: { ...devices["Desktop Chrome"] },
    },
  ],
});
