// Bundle discipline, two lanes:
//   - non-docs pages: no fetched scripts EXCEPT the two same-origin Vercel
//     telemetry loaders (ADR-0029, owner directive — the sole sanctioned
//     exception); the only other JS is inline and ≤10 KB total per page (the
//     /demo island lives inside that gate and is additionally capped in
//     demo.spec.ts).
//   - docs pages: same rule BEFORE interaction; after a search gesture, every
//     additional fetched URL must be the same-origin Pagefind bundle.
// No request ever leaves the preview origin on any page (the telemetry
// loaders and their beacons are same-origin /_vercel/ paths; locally they 404
// and nothing beacons).
import { expect, test } from "@playwright/test";
import { ALL_PAGES, DOCS_PAGES, NON_DOCS_PAGES } from "./pages";

const JS_BUDGET_BYTES = 10 * 1024;
const ORIGIN_HOST = "localhost:4977";
// The exact allowlist ADR-0029 sanctions — nothing else may be fetched.
const VERCEL_TELEMETRY = /^\/_vercel\/(insights|speed-insights)\/script\.js$/;

function track(page: import("@playwright/test").Page) {
  const external: string[] = [];
  const scripts: string[] = [];
  page.on("request", (req) => {
    const url = new URL(req.url());
    if (url.host !== ORIGIN_HOST) external.push(req.url());
    if (req.resourceType() === "script" && !VERCEL_TELEMETRY.test(url.pathname)) scripts.push(url.pathname);
  });
  return { external, scripts };
}

for (const path of NON_DOCS_PAGES) {
  test(`budget + network (no fetched JS beyond the ADR-0029 telemetry loaders): ${path}`, async ({ page }) => {
    const { external, scripts } = track(page);
    await page.goto(path, { waitUntil: "networkidle" });
    expect(external, external.join("\n")).toEqual([]);
    expect(scripts, scripts.join("\n")).toEqual([]);
    const inlineJsBytes = await page.evaluate(() =>
      Array.from(document.querySelectorAll("script")).reduce((sum, s) => sum + (s.textContent?.length ?? 0), 0),
    );
    expect(inlineJsBytes).toBeLessThanOrEqual(JS_BUDGET_BYTES);
  });
}

for (const path of DOCS_PAGES) {
  test(`budget + network (docs lane, pre-interaction): ${path}`, async ({ page }) => {
    const { external, scripts } = track(page);
    await page.goto(path, { waitUntil: "networkidle" });
    expect(external, external.join("\n")).toEqual([]);
    // No fetched scripts before any user gesture (beyond the ADR-0029
    // telemetry loaders the tracker already accounts for), docs pages included.
    expect(scripts, scripts.join("\n")).toEqual([]);
    const inlineJsBytes = await page.evaluate(() =>
      Array.from(document.querySelectorAll("script")).reduce((sum, s) => sum + (s.textContent?.length ?? 0), 0),
    );
    expect(inlineJsBytes).toBeLessThanOrEqual(JS_BUDGET_BYTES);
  });
}

test("docs search: after a gesture, only same-origin /pagefind/ is fetched", async ({ page }) => {
  const { external } = track(page);
  const fetched: string[] = [];
  page.on("request", (req) => {
    const url = new URL(req.url());
    if (VERCEL_TELEMETRY.test(url.pathname)) return; // ADR-0029 loaders, accounted for above
    if (url.host === ORIGIN_HOST && (url.pathname.startsWith("/pagefind/") || req.resourceType() === "script"))
      fetched.push(url.pathname);
  });
  await page.goto("/docs/search/", { waitUntil: "networkidle" });
  await page.locator("#docs-search-input").click();
  await page.locator("#pagefind-container input").waitFor({ state: "visible" });
  await page.locator("#pagefind-container input").fill("reconciliation");
  await page.locator(".pagefind-ui__result").first().waitFor({ state: "visible" });
  await page.waitForLoadState("networkidle");
  expect(external, external.join("\n")).toEqual([]);
  expect(fetched.length).toBeGreaterThan(0);
  for (const p of fetched) expect(p, `unexpected fetch ${p}`).toMatch(/^\/pagefind\//);
});
