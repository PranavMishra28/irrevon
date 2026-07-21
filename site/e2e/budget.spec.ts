// Bundle discipline: zero JS by default with the inline theme toggle as the
// only script (≤10 KB total per page; goal ≤5 KB), and no request ever leaves
// the preview origin (self-hosted fonts, no telemetry, no analytics).
import { expect, test } from "@playwright/test";
import { PAGES } from "./pages";

const JS_BUDGET_BYTES = 10 * 1024;

for (const path of PAGES) {
  test(`budget + network: ${path}`, async ({ page }) => {
    const external: string[] = [];
    const jsRequests: string[] = [];
    page.on("request", (req) => {
      const url = new URL(req.url());
      if (url.host !== "localhost:4977") external.push(req.url());
      if (req.resourceType() === "script") jsRequests.push(req.url());
    });

    await page.goto(path, { waitUntil: "networkidle" });

    // No external requests, ever.
    expect(external, external.join("\n")).toEqual([]);
    // Zero JS files fetched — the only scripts are inline.
    expect(jsRequests, jsRequests.join("\n")).toEqual([]);

    const inlineJsBytes = await page.evaluate(() =>
      Array.from(document.querySelectorAll("script")).reduce((sum, s) => sum + (s.textContent?.length ?? 0), 0),
    );
    expect(inlineJsBytes).toBeLessThanOrEqual(JS_BUDGET_BYTES);
  });
}
