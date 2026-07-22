// Internal link validity: every same-origin href on every page resolves, and
// every fragment target exists. External links are shape-checked only (no
// network beyond the preview server).
import { expect, test } from "@playwright/test";
import { PAGES } from "./pages";

test("internal links resolve and fragments exist", async ({ page, request }) => {
  const seen = new Set<string>();
  const failures: string[] = [];

  for (const path of PAGES) {
    await page.goto(path);
    const hrefs = await page.locator("a[href]").evaluateAll((as) => as.map((a) => a.getAttribute("href") ?? ""));
    for (const href of hrefs) {
      if (href.startsWith("http://") || href.startsWith("https://")) {
        if (!/^https?:\/\/[\w.-]+(\/[^\s]*)?$/.test(href)) failures.push(`${path}: malformed external ${href}`);
        continue;
      }
      if (href.startsWith("mailto:")) {
        failures.push(`${path}: unexpected mailto ${href}`);
        continue;
      }
      const [target, fragment] = href.split("#");
      if (target && !seen.has(target)) {
        seen.add(target);
        const res = await request.get(target);
        if (res.status() !== 200) failures.push(`${path}: ${target} -> ${res.status()}`);
      }
      if (fragment) {
        const base = target || path;
        await page.goto(base);
        const found = await page.evaluate((id) => document.getElementById(id) !== null, fragment);
        if (!found) failures.push(`${path}: missing fragment #${fragment} on ${base}`);
        await page.goto(path);
      }
    }
  }
  expect(failures, failures.join("\n")).toEqual([]);
});

test("nav lists exactly the built pages — no dead item", async ({ page }) => {
  await page.goto("/");
  const hrefs = await page
    .locator("nav[aria-label='Primary'] a")
    .evaluateAll((as) => as.map((a) => a.getAttribute("href")));
  expect(hrefs).toEqual([
    "/platform/",
    "/how-it-works/",
    "/demo/",
    "/benchmark/",
    "/docs/",
    "/research/",
    "/install/",
  ]);
});
