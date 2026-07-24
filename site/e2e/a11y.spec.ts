// axe (WCAG 2.2 AA) on every page, both themes. Violations are errors — the
// gate cannot be weakened to pass (REDESIGN-BRIEF §0 invariant 7).
import AxeBuilder from "@axe-core/playwright";
import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";
import { ALL_PAGES } from "./pages";

for (const path of ALL_PAGES) {
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

// The /demo stepper's stepped states are distinct UI (controls visible, one
// beat collapsed in) — axe them separately in both themes at representative
// beats (the CLICK beat and the compound final beat).
for (const theme of ["light", "dark"] as const) {
  test(`axe: /demo/ stepped states [${theme}]`, async ({ page }) => {
    await page.emulateMedia({ colorScheme: theme });
    await page.goto("/demo/");
    for (const beat of [5, 12]) {
      await page.locator(`.beat-tick[data-n="${beat}"]`).click();
      await page.waitForTimeout(250);
      const results = await new AxeBuilder({ page })
        .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa", "best-practice"])
        .analyze();
      expect(
        results.violations,
        results.violations.map((v) => `beat ${beat} ${v.id}: ${v.nodes.map((n) => n.target.join(" ")).join("; ")}`).join("\n"),
      ).toEqual([]);
    }
  });
}

test("keyboard: skip link is first tab stop and lands on main", async ({ page }) => {
  await page.goto("/");
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  const skipFocus = await page.locator(".skip-link").evaluate((link) => {
    const style = getComputedStyle(link);
    return { outlineStyle: style.outlineStyle, outlineWidth: style.outlineWidth, transform: style.transform };
  });
  expect(skipFocus.outlineStyle).not.toBe("none");
  expect(Number.parseFloat(skipFocus.outlineWidth)).toBeGreaterThanOrEqual(3);
  expect(skipFocus.transform).toBe("none");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/#main$/);
  await expect(page.locator("main#main")).toHaveAttribute("tabindex", "-1");
  await expect(page.locator("main#main")).toBeFocused();
});

test("semantics: Home citation wrapper does not nest paragraphs", async ({ page }) => {
  await page.goto("/");
  const wrapper = page.locator(".hero-proof-src");
  await expect(wrapper).toHaveCount(1);
  await expect(wrapper).toHaveJSProperty("tagName", "DIV");
  await expect(wrapper.locator(":scope > p.claim-source")).toHaveCount(1);
  await expect(page.locator("p p")).toHaveCount(0);
});

test("fonts: every self-hosted face uses non-blocking swap", () => {
  const css = readFileSync(new URL("../src/styles/site.css", import.meta.url), "utf8");
  const faces = [...css.matchAll(/@font-face\s*{([\s\S]*?)}/g)].map((match) => match[1]);
  expect(faces).toHaveLength(5);
  for (const face of faces) expect(face).toMatch(/font-display:\s*swap\s*;/);
  expect(css).not.toMatch(/font-display:\s*block\s*;/);
});

test("forced colors: critical controls retain boundaries, state, and focus", async ({ browser, page }) => {
  await page.emulateMedia({ forcedColors: "active" });
  await page.goto("/");
  expect(await page.evaluate(() => matchMedia("(forced-colors: active)").matches)).toBe(true);

  const primary = page.locator(".btn-primary").first();
  await primary.focus();
  const primaryStyle = await primary.evaluate((control) => {
    const style = getComputedStyle(control);
    return {
      borderStyle: style.borderTopStyle,
      borderWidth: style.borderTopWidth,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
    };
  });
  expect(primaryStyle.borderStyle).toBe("solid");
  expect(Number.parseFloat(primaryStyle.borderWidth)).toBeGreaterThanOrEqual(1);
  expect(primaryStyle.outlineStyle).not.toBe("none");
  expect(Number.parseFloat(primaryStyle.outlineWidth)).toBeGreaterThanOrEqual(3);

  // Keep the progressively enhanced search form in its no-JS state so the
  // Pagefind upgrade cannot replace the focused native input mid-assertion.
  const noJsContext = await browser.newContext({ forcedColors: "active", javaScriptEnabled: false });
  const noJsPage = await noJsContext.newPage();
  await noJsPage.goto("/docs/search/");
  const search = noJsPage.locator("#docs-search-input");
  await search.focus();
  const searchStyle = await search.evaluate((control) => {
    const style = getComputedStyle(control);
    return {
      borderStyle: style.borderTopStyle,
      borderWidth: style.borderTopWidth,
      outlineStyle: style.outlineStyle,
      outlineWidth: style.outlineWidth,
    };
  });
  expect(searchStyle.borderStyle).toBe("solid");
  expect(Number.parseFloat(searchStyle.borderWidth)).toBeGreaterThanOrEqual(1);
  expect(searchStyle.outlineStyle).not.toBe("none");
  expect(Number.parseFloat(searchStyle.outlineWidth)).toBeGreaterThanOrEqual(2);
  await noJsContext.close();
});

test("keyboard: nav links and theme toggle are reachable and operable", async ({ page }) => {
  await page.emulateMedia({ colorScheme: "light" });
  await page.goto("/");
  await expect(page.locator("nav[aria-label='Primary']")).toBeVisible();
  await expect(page.locator("nav[aria-label='Primary'] a").first()).toBeVisible();
  const toggle = page.locator("#theme-toggle");
  await expect(toggle).toBeVisible();
  await expect(toggle).toHaveAttribute("aria-label", "Switch to dark theme");
  await toggle.focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  await expect(toggle).toHaveAttribute("aria-label", "Switch to light theme");
});

test("responsive: phone navigation is compact and keyboard-operable", async ({ page }) => {
  for (const width of [390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    const button = page.locator("#menu-toggle");
    await expect(button).toBeVisible();
    await expect(button).toHaveAttribute("aria-expanded", "false");
    await expect(page.locator("nav[aria-label='Primary']")).toBeHidden();
    expect(await page.locator(".site-header").evaluate((header) => header.getBoundingClientRect().height)).toBeLessThan(120);
    await button.focus();
    await page.keyboard.press("Enter");
    await expect(button).toHaveAttribute("aria-expanded", "true");
    await expect(page.locator("nav[aria-label='Primary'] a")).toHaveCount(8);
    await expect(page.locator("nav[aria-label='Primary'] a").first()).toBeVisible();
    await page.keyboard.press("Enter");
    await expect(button).toHaveAttribute("aria-expanded", "false");
  }
});

test("responsive: every page avoids viewport-level horizontal overflow", async ({ page }) => {
  for (const width of [1440, 1024, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    for (const theme of ["light", "dark"] as const) {
      await page.emulateMedia({ colorScheme: theme });
      for (const path of ALL_PAGES) {
        await page.goto(path);
        const viewport = await page.evaluate(() => ({
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
        }));
        expect(
          viewport.scrollWidth,
          `${path} widened the ${width}px ${theme} viewport`,
        ).toBeLessThanOrEqual(viewport.clientWidth);
      }
    }
  }
});

test("reduced motion: representative product surfaces render with reduce preference", async ({ page }) => {
  await page.emulateMedia({ reducedMotion: "reduce" });
  for (const path of ["/", "/how-it-works/", "/demo/", "/benchmark/", "/docs/", "/install/"]) {
    await page.goto(path);
    await expect(page.locator("h1")).toBeVisible();
    const activeAnimations = await page.locator("*").evaluateAll((elements) =>
      elements.reduce(
        (count, element) =>
          count +
          element.getAnimations().filter(
            (animation) => animation.playState === "running" && animation.effect?.getTiming().duration !== 0,
          ).length,
        0,
      ),
    );
    expect(activeAnimations, `${path} retains motion under reduce`).toBe(0);
  }
});

test("no-JS: content and nav render without JavaScript", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/");
  await expect(page.locator("h1")).toBeVisible();
  await expect(page.locator("nav[aria-label='Primary'] a")).toHaveCount(8);
  // The theme toggle is JS-only and must stay hidden without it.
  await expect(page.locator("#theme-toggle")).toBeHidden();
  await context.close();
});
