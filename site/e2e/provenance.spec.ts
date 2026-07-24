import { expect, test } from "@playwright/test";

test("version manifest exposes complete, non-placeholder build provenance", async ({ request }) => {
  const response = await request.get("/version.json");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("application/json");
  const manifest = await response.json();
  expect(manifest).toEqual({
    release_version: expect.stringMatching(/^\d+\.\d+\.\d+(?:[.+-][0-9A-Za-z.-]+)?$/),
    commit_sha: expect.stringMatching(/^[0-9a-f]{40}$/),
    built_at: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/),
    benchmark_harness_version: expect.stringMatching(/^\d+\.\d+\.\d+$/),
    schema_version: expect.stringMatching(/^\d+$/),
    environment: expect.stringMatching(/^(production|preview|development)$/),
  });
});

test("claim provenance links identify the selected generated registry row", async ({ page }) => {
  await page.goto("/");
  const hrefs = await page
    .locator(".claim-source a")
    .evaluateAll((links) => links.slice(0, 2).map((link) => (link as HTMLAnchorElement).href));
  expect(hrefs).toHaveLength(2);
  expect(new URL(hrefs[0]).hash).toBe("#claim-problem-ambiguous-outcome");
  expect(new URL(hrefs[1]).hash).toBe("#claim-demo-contrast");
  expect(hrefs[0]).not.toBe(hrefs[1]);
});
