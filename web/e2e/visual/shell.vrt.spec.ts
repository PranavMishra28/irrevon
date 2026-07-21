import { expect, test } from "@playwright/test";

/**
 * VRT baselines are authoritative only from the pinned Linux container
 * (make web-vrt). The project is skipped outside it via playwright.config.ts.
 */
const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";

const SCREENS = [
  ["learn-start", "/learn/start"],
  ["learn-identity", "/learn/identity"],
  ["learn-state", "/learn/state"],
  ["learn-tiers", "/learn/tiers"],
  ["effects-grid", "/effects"],
  ["effects-filtered", "/effects?lifecycle=AMBIGUOUS"],
  ["effect-detail", `/effects/${FLAGSHIP}`],
  ["findings", "/findings"],
  ["adapters", "/adapters"],
  ["demo-start", "/demo"],
  ["health", "/health"],
  ["bench-no-runs", "/bench"],
  ["taxonomy", "/taxonomy"],
] as const;

const VIEWPORTS = [
  { width: 1280, height: 800 },
  { width: 1600, height: 900 },
] as const;

for (const theme of ["light", "dark"] as const) {
  for (const viewport of VIEWPORTS) {
    test.describe(`${theme} ${viewport.width}`, () => {
      test.use({ viewport: { width: viewport.width, height: viewport.height } });

      for (const [name, route] of SCREENS) {
        test(name, async ({ page }) => {
          await page.goto(route);
          await page.evaluate((t) => {
            document.documentElement.setAttribute("data-theme", t);
            return document.fonts.ready;
          }, theme);
          await expect(page).toHaveScreenshot(`${name}-${viewport.width}-${theme}.png`, {
            fullPage: true,
          });
        });
      }

      test("palette-open", async ({ page }) => {
        await page.goto("/learn/start");
        await page.getByRole("button", { name: /Go to…/ }).waitFor();
        await page.evaluate((t) => {
          document.documentElement.setAttribute("data-theme", t);
          return document.fonts.ready;
        }, theme);
        await page.keyboard.press("ControlOrMeta+k");
        await expect(page.getByPlaceholder(/Go to view/)).toBeFocused();
        await expect(page).toHaveScreenshot(`palette-${viewport.width}-${theme}.png`);
      });
    });
  }
}
