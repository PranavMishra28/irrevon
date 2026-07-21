import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const MISSING = "f".repeat(64);

const ROUTES = [
  "/learn/start",
  "/learn/identity",
  "/learn/state",
  "/learn/tiers",
  "/effects",
  "/effects?lifecycle=AMBIGUOUS",
  `/effects/${FLAGSHIP}`,
  `/effects/${MISSING}`,
  "/demo",
  "/health",
  "/attention",
  "/findings",
  "/adapters",
  "/bench",
  "/taxonomy",
];

const TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

for (const theme of ["light", "dark"] as const) {
  test.describe(`axe WCAG 2.2 AA — ${theme}`, () => {
    for (const route of ROUTES) {
      test(route, async ({ page }) => {
        await page.goto(route);
        await page.evaluate((t) => {
          document.documentElement.setAttribute("data-theme", t);
        }, theme);
        await page.waitForLoadState("networkidle");
        const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
        expect(results.violations).toEqual([]);
      });
    }

    test(`palette open — ${theme}`, async ({ page }) => {
      await page.goto("/learn/start");
      await page.getByRole("button", { name: /Go to…/ }).waitFor();
      await page.evaluate((t) => {
        document.documentElement.setAttribute("data-theme", t);
      }, theme);
      await page.keyboard.press("ControlOrMeta+k");
      await expect(page.getByPlaceholder(/Go to view/)).toBeFocused();
      const results = await new AxeBuilder({ page }).withTags(TAGS).analyze();
      expect(results.violations).toEqual([]);
    });
  });
}

test("interactive targets in chrome meet 24px minimum or spacing exception", async ({
  page,
}) => {
  await page.goto("/learn/start");
  const boxes = await page.$$eval("header button, header a", (els) =>
    els.map((el) => {
      const r = el.getBoundingClientRect();
      return { w: r.width, h: r.height, label: el.textContent };
    }),
  );
  for (const box of boxes) {
    expect(box.w, `${box.label} width`).toBeGreaterThanOrEqual(24);
    expect(box.h, `${box.label} height`).toBeGreaterThanOrEqual(24);
  }
});

test("320px reflow: no body-level horizontal scrolling on prose routes", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 800 });
  for (const route of ["/learn/start", "/learn/identity", "/learn/tiers", "/health"]) {
    await page.goto(route);
    const overflow = await page.evaluate(() => {
      const root = document.scrollingElement ?? document.documentElement;
      return root.scrollWidth > root.clientWidth;
    });
    expect(overflow, `body overflow at 320px on ${route}`).toBe(false);
  }
});

test("reduced motion collapses every motion token to zero", async ({ browser }) => {
  const context = await browser.newContext({ reducedMotion: "reduce" });
  const page = await context.newPage();
  await page.goto("/learn/start");
  const durations = await page.evaluate(() => {
    const styles = getComputedStyle(document.documentElement);
    return ["--sys-dur-fast", "--sys-dur-base", "--sys-dur-slow"].map((token) =>
      styles.getPropertyValue(token).trim(),
    );
  });
  for (const duration of durations) {
    // Browsers normalize 0ms to 0s in computed custom-property values.
    expect(["0ms", "0s"]).toContain(duration);
  }
  await context.close();
});
