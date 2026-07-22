import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * VRT baselines are authoritative only from the pinned Linux container
 * (make web-vrt). The project is skipped outside it via playwright.config.ts.
 * Matrix: the historical 1280/1600 desktop screens plus the redesign's
 * curated 375/768 responsive baselines (REDESIGN-BRIEF §7.5).
 */
const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const ORPHAN_SELECTED = "/findings?selected=fnd_00000000000000000004";

const SCREENS = [
  ["overview", "/"],
  ["learn-start", "/learn/start"],
  ["learn-identity", "/learn/identity"],
  ["learn-state", "/learn/state"],
  ["learn-tiers", "/learn/tiers"],
  ["effects-grid", "/effects"],
  ["effects-filtered", "/effects?lifecycle=AMBIGUOUS"],
  ["effect-detail", `/effects/${FLAGSHIP}`],
  ["effect-detail-selected", `/effects/${FLAGSHIP}?selected=node:attempt:1`],
  ["findings", "/findings"],
  ["attention", "/attention"],
  ["adapters", "/adapters"],
  ["demo-start", "/demo"],
  ["health", "/health"],
  ["bench-no-runs", "/bench"],
  ["taxonomy", "/taxonomy"],
] as const;

/** Curated 375 baselines: every major surface in its phone projection. */
const MOBILE_SCREENS = [
  ["m-overview", "/"],
  ["m-effects-cards", "/effects"],
  ["m-effect-graph-vertical", `/effects/${FLAGSHIP}`],
  ["m-findings-orphan", ORPHAN_SELECTED],
  ["m-attention", "/attention"],
  ["m-adapters-topology", "/adapters"],
  ["m-demo-lane", "/demo?lane=irrevon"],
  ["m-health", "/health"],
  ["m-bench", "/bench"],
] as const;

/** Curated 768 baselines. */
const TABLET_SCREENS = [
  ["t-overview", "/"],
  ["t-effects", "/effects"],
  ["t-effect-graph", `/effects/${FLAGSHIP}`],
  ["t-findings", "/findings"],
  ["t-demo", "/demo"],
] as const;

const VIEWPORTS = [
  { width: 1280, height: 800 },
  { width: 1600, height: 900 },
] as const;

async function settle(page: Page, theme: string) {
  // Deterministic render barrier — goto resolves on the load event, BEFORE
  // React mounts and data queries settle. Without it the screenshot races
  // the render (observed: a blank full-page capture).
  await page.getByRole("button", { name: /Go to…/ }).waitFor();
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
  await page.evaluate((t) => {
    document.documentElement.setAttribute("data-theme", t);
    return document.fonts.ready;
  }, theme);
}

for (const theme of ["light", "dark"] as const) {
  for (const viewport of VIEWPORTS) {
    test.describe(`${theme} ${viewport.width}`, () => {
      test.use({ viewport: { width: viewport.width, height: viewport.height } });

      for (const [name, route] of SCREENS) {
        test(name, async ({ page }) => {
          await page.goto(route);
          await settle(page, theme);
          await expect(page).toHaveScreenshot(`${name}-${viewport.width}-${theme}.png`, {
            fullPage: true,
          });
        });
      }

      test("palette-open", async ({ page }) => {
        await page.goto("/learn/start");
        await settle(page, theme);
        await page.keyboard.press("ControlOrMeta+k");
        await expect(page.getByPlaceholder(/Go to view/)).toBeFocused();
        await expect(page).toHaveScreenshot(`palette-${viewport.width}-${theme}.png`);
      });
    });
  }

  test.describe(`${theme} 375`, () => {
    test.use({ viewport: { width: 375, height: 812 } });

    for (const [name, route] of MOBILE_SCREENS) {
      test(name, async ({ page }) => {
        await page.goto(route);
        await settle(page, theme);
        await expect(page).toHaveScreenshot(`${name}-375-${theme}.png`, { fullPage: true });
      });
    }

    test("m-drawer", async ({ page }) => {
      await page.goto("/learn/start");
      await settle(page, theme);
      await page.getByRole("button", { name: "Menu" }).click();
      await expect(page.getByRole("button", { name: "Close menu" })).toBeFocused();
      await expect(page).toHaveScreenshot(`m-drawer-375-${theme}.png`);
    });
  });

  test.describe(`${theme} 768`, () => {
    test.use({ viewport: { width: 768, height: 1024 } });

    for (const [name, route] of TABLET_SCREENS) {
      test(name, async ({ page }) => {
        await page.goto(route);
        await settle(page, theme);
        await expect(page).toHaveScreenshot(`${name}-768-${theme}.png`, { fullPage: true });
      });
    }
  });
}
