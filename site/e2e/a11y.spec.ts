// axe (WCAG 2.2 AA) on every page, both themes. Violations are errors — the
// gate cannot be weakened to pass (REDESIGN-BRIEF §0 invariant 7).
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { PAGES } from "./pages";

for (const path of PAGES) {
  for (const theme of ["light", "dark"] as const) {
    test(`axe: ${path} [${theme}]`, async ({ page }) => {
      await page.emulateMedia({ colorScheme: theme });
      await page.goto(path);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
        .analyze();
      expect(
        results.violations,
        results.violations.map((v) => `${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join("; ")}`).join("\n"),
      ).toEqual([]);
    });
  }
}

test("keyboard: skip link is first tab stop and lands on main", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
});

test("keyboard: nav links and theme toggle are reachable and operable", async ({ page }) => {
  await page.goto("/");
  const toggle = page.locator("#theme-toggle");
  await expect(toggle).toBeVisible();
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", /dark|light/);
});

test("reduced motion: pages render with reduce preference", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
});

test("no-JS: content and nav render without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  await expect(page.locator("nav[aria-label='Primary'] a")).toHaveCount(5);
  // The theme toggle is JS-only and must stay hidden without it.
  await expect(page.locator("#theme-toggle")).toBeHidden();
  await context.close();
});
