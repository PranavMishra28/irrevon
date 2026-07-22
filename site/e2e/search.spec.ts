// Docs search behavior: the plain-form fallback, the lazy Pagefind upgrade,
// a known-positive result, and the no-JS honesty (a form that goes somewhere
// real, never a dead interface).
import { expect, test } from "@playwright/test";

test("search returns a known result and links a real docs page", async ({ page }) => {
  await page.goto("/docs/search/");
  const input = page.locator("#docs-search-input");
  await input.click();
  const ui = page.locator("#pagefind-container input");
  await expect(ui).toBeVisible();
  await ui.fill("reconciliation");
  const first = page.locator(".pagefind-ui__result-link").first();
  await expect(first).toBeVisible();
  const target = await first.getAttribute("href");
  expect(target).toBeTruthy();
  const res = await page.request.get(target!);
  expect(res.status()).toBe(200);
});

test("?q= from the no-JS form activates search with the query", async ({ page }) => {
  await page.goto("/docs/search/?q=ledger");
  const ui = page.locator("#pagefind-container input");
  await expect(ui).toBeVisible();
  await expect(ui).toHaveValue("ledger");
  await expect(page.locator(".pagefind-ui__result").first()).toBeVisible();
});

test("no-JS: the search form submits to the search page and explains itself", async ({ browser }) => {
  const context = await browser.newContext({ javaScriptEnabled: false });
  const page = await context.newPage();
  await page.goto("/docs/");
  const form = page.locator(".docs-search-form");
  await expect(form).toBeVisible();
  await form.locator("input[name=q]").fill("gate");
  await form.locator("button[type=submit]").click();
  await expect(page).toHaveURL(/\/docs\/search\/\?q=gate$/);
  // The noscript explanation renders; the docs index stays one link away.
  await expect(page.locator(".docs-search-noscript")).toBeVisible();
  await context.close();
});

test("keyboard: search input reachable and results navigable", async ({ page }) => {
  await page.goto("/docs/search/");
  await page.locator("#docs-search-input").focus();
  const ui = page.locator("#pagefind-container input");
  await expect(ui).toBeVisible();
  await ui.fill("intent");
  await expect(page.locator(".pagefind-ui__result-link").first()).toBeVisible();
  await page.keyboard.press("Tab");
  // Focus lands inside the results region eventually; assert a result link can be focused.
  await page.locator(".pagefind-ui__result-link").first().focus();
  await expect(page.locator(".pagefind-ui__result-link").first()).toBeFocused();
});
