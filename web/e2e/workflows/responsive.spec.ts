import { expect, test } from "@playwright/test";

/**
 * Responsive/reflow matrix (REDESIGN-BRIEF §7.4): every route at
 * 320/375/768/1120/1440 — no body-level horizontal scroll and no clipped
 * focused element. Target sizes: 44px under coarse/mobile widths for the
 * primary controls; 24px on desktop (checked in the a11y suite).
 */

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";

const ROUTES = [
  "/",
  "/effects",
  `/effects/${FLAGSHIP}`,
  "/findings",
  "/attention",
  "/adapters",
  "/demo",
  "/bench",
  "/learn/start",
  "/learn/state",
  "/health",
];

const VIEWPORTS = [
  { width: 320, height: 800 },
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1120, height: 800 },
  { width: 1440, height: 900 },
];

for (const viewport of VIEWPORTS) {
  test(`no body horizontal scroll on any route at ${viewport.width}`, async ({ page }) => {
    await page.setViewportSize(viewport);
    for (const route of ROUTES) {
      await page.goto(route);
      await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
      await page.waitForLoadState("networkidle");
      const overflow = await page.evaluate(() => {
        const root = document.scrollingElement ?? document.documentElement;
        return root.scrollWidth > root.clientWidth;
      });
      expect(overflow, `body overflow on ${route} at ${viewport.width}`).toBe(false);
    }
  });
}

test("focused elements are not clipped out of the viewport at 320", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  await page.goto("/effects");
  await expect(page.getByRole("heading", { name: "Effects" })).toBeVisible();
  // Tab through the first dozen stops; every focused element must have a
  // visible box inside the horizontal viewport.
  for (let i = 0; i < 12; i += 1) {
    await page.keyboard.press("Tab");
    const box = await page.evaluate(() => {
      const el = document.activeElement;
      if (!(el instanceof HTMLElement) || el === document.body) return null;
      const rect = el.getBoundingClientRect();
      return { left: rect.left, right: rect.right, width: rect.width };
    });
    if (box === null) continue;
    expect(box.right, `tab stop ${i} clipped left`).toBeGreaterThan(0);
    expect(box.left, `tab stop ${i} clipped right`).toBeLessThan(320);
  }
});

test("44px targets under mobile width for primary route controls", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });

  // Shell chrome.
  await page.goto("/learn/start");
  for (const name of ["Go to…", "Menu"]) {
    const box = await page.getByRole("button", { name, exact: true }).boundingBox();
    expect(box?.height ?? 0, `${name} height`).toBeGreaterThanOrEqual(44);
    expect(box?.width ?? 0, `${name} width`).toBeGreaterThanOrEqual(44);
  }

  // Learn subnav menu.
  const select = page.locator("select");
  const selectBox = await select.boundingBox();
  expect(selectBox?.height ?? 0).toBeGreaterThanOrEqual(44);

  // Investigation projection tabs.
  await page.goto(`/effects/${FLAGSHIP}`);
  const tab = page
    .getByRole("tablist", { name: "Investigation projections" })
    .getByRole("tab", { name: "timeline" });
  const tabBox = await tab.boundingBox();
  expect(tabBox?.height ?? 0).toBeGreaterThanOrEqual(44);
});

test("200% zoom equivalent (640px effective) keeps prose routes readable", async ({ page }) => {
  // 1280 viewport at 200% zoom ≈ 640px layout width.
  await page.setViewportSize({ width: 640, height: 800 });
  for (const route of ["/learn/start", "/health", "/bench"]) {
    await page.goto(route);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow, `overflow at 640 on ${route}`).toBe(false);
  }
});

test("reduced motion: seat/drawer/graph motion collapses; demo steps stay discrete", async ({
  browser,
}) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/");
  const durations = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return ["--sys-dur-fast", "--sys-dur-base", "--sys-dur-slow", "--sys-dur-seat"].map(
      (token) => styles.getPropertyValue(token).trim(),
    );
  });
  for (const duration of durations) {
    expect(["0ms", "0s"]).toContain(duration);
  }
  // Selection under reduced motion is instant and complete.
  await page.goto(`/effects/${FLAGSHIP}?selected=node:attempt:1`);
  await expect(page.getByTestId("graph-inspector")).toBeVisible();
  // Demo stepping works with zero transition time.
  await page.goto("/demo");
  await page.getByRole("button", { name: "Next →" }).click();
  await expect(page.getByText("2 / 11")).toBeVisible();
  await context.close();
});
