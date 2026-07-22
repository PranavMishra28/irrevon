import { storybookTest } from "@storybook/addon-vitest/vitest-plugin";
import react from "@vitejs/plugin-react";
import { playwright } from "@vitest/browser-playwright";
import { defineConfig } from "vitest/config";

/**
 * Two projects:
 * - unit: pure logic in node, zero retries (a flake is a bug)
 * - storybook: stories as browser-mode tests via the Storybook addon,
 *   with axe checks registered in .storybook/vitest.setup.ts
 */
export default defineConfig({
  resolve: {
    alias: { "@": new URL("./src", import.meta.url).pathname },
  },
  // Mirror the vite.config.ts define so modules that read the build-time
  // data mode (data-mode.ts and its importers) load under test.
  define: { __IRREVON_DATA_MODE__: JSON.stringify("mock") },
  test: {
    retry: 0,
    projects: [
      {
        extends: true,
        plugins: [react()],
        test: {
          name: "unit",
          environment: "node",
          include: ["src/**/*.test.ts"],
        },
      },
      {
        extends: true,
        plugins: [react(), storybookTest({ configDir: ".storybook" })],
        test: {
          name: "storybook",
          browser: {
            enabled: true,
            headless: true,
            provider: playwright(),
            instances: [{ browser: "chromium" }],
          },
        },
      },
    ],
  },
});
