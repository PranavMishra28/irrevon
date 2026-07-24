// SEO/metadata gates: canonical + OG/Twitter + referrer + CSP meta on every
// page (with hashes matching the actual inline scripts — the JS-creep drift
// gate), sitemap correctness, robots.txt, RSS validity, JSON-LD honesty
// (SoftwareSourceCode, never SoftwareApplication; no offers/ratings/reviews
// anywhere — nothing exists to offer or rate). The broader built-output
// contract lives in discoverability.spec.ts.
import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";
import { ALL_PAGES, PAGES } from "./pages";
import { isIndexablePath } from "../search-policy.mjs";

for (const path of ALL_PAGES) {
  test(`metadata: ${path}`, async ({ page }) => {
    await page.goto(path);
    if (path !== "/404.html") {
      await expect(page.locator("link[rel=canonical]")).toHaveCount(1);
      const canonical = await page.locator("link[rel=canonical]").getAttribute("href");
      expect(canonical).toContain("://");
    }
    await expect(page.locator("meta[property='og:title']")).toHaveCount(1);
    await expect(page.locator("meta[property='og:image']")).toHaveCount(1);
    await expect(page.locator("meta[name='twitter:card']")).toHaveAttribute("content", "summary_large_image");
    await expect(page.locator("meta[name='referrer']")).toHaveAttribute("content", "strict-origin-when-cross-origin");
    // The OG image resolves on this origin.
    const og = await page.locator("meta[property='og:image']").getAttribute("content");
    const res = await page.request.get(og!.replace(/^https?:\/\/[^/]+/, ""));
    expect(res.status(), `og:image ${og} unreachable`).toBe(200);
  });

  test(`CSP meta present with matching script hashes: ${path}`, async ({ page }) => {
    await page.goto(path);
    const policy = await page.locator("meta[http-equiv='Content-Security-Policy']").getAttribute("content");
    expect(policy).toBeTruthy();
    expect(policy).toContain("default-src 'none'");
    const inline = await page.evaluate(() =>
      Array.from(document.querySelectorAll("script:not([src])"))
        .filter((s) => s.getAttribute("type") !== "application/ld+json")
        .map((s) => s.textContent ?? ""),
    );
    for (const body of inline) {
      const hash = createHash("sha256").update(body).digest("base64");
      expect(policy, `missing hash for an inline script on ${path}`).toContain(`'sha256-${hash}'`);
    }
  });
}

test("sitemap exists, covers indexable pages, excludes noindex/error pages", async ({ request }) => {
  const index = await request.get("/sitemap-index.xml");
  expect(index.status()).toBe(200);
  const sub = await request.get("/sitemap-0.xml");
  expect(sub.status()).toBe(200);
  const xml = await sub.text();
  for (const p of PAGES.filter((path) => isIndexablePath(path))) {
    expect(xml, `sitemap missing ${p}`).toContain(`${p}</loc>`);
  }
  expect(xml).not.toContain("/404");
  expect(xml).not.toContain("/docs/search/");
});

test("robots.txt allows all and names the sitemap", async ({ request }) => {
  const res = await request.get("/robots.txt");
  expect(res.status()).toBe(200);
  const body = await res.text();
  expect(body).toContain("User-agent: *");
  expect(body).toContain("Allow: /");
  expect(body).toMatch(/Sitemap: https?:\/\/.+\/sitemap-index\.xml/);
});

test("research RSS is valid-shaped and lists the posts", async ({ request }) => {
  const res = await request.get("/research/rss.xml");
  expect(res.status()).toBe(200);
  const xml = await res.text();
  expect(xml).toContain("<rss");
  expect((xml.match(/<item>/g) ?? []).length).toBeGreaterThanOrEqual(2);
  expect(xml).toContain("Preregistering a benchmark");
});

test("research pages advertise the feed", async ({ page }) => {
  await page.goto("/research/");
  await expect(page.locator("link[rel=alternate][type='application/rss+xml']")).toHaveCount(1);
});

test("JSON-LD: home is SoftwareSourceCode + WebSite without retired SearchAction", async ({ page }) => {
  await page.goto("/");
  const blocks = await page
    .locator("script[type='application/ld+json']")
    .evaluateAll((els) => els.map((e) => JSON.parse(e.textContent ?? "{}")));
  const types = blocks.map((b) => b["@type"]);
  expect(types).toContain("SoftwareSourceCode");
  expect(types).toContain("WebSite");
  expect(types).not.toContain("SoftwareApplication");
  const source = blocks.find((b) => b["@type"] === "SoftwareSourceCode");
  expect(source).toBeTruthy();
  expect(source!.license).toContain(`${source!.codeRepository}/blob/`);
  expect(source!.license).toMatch(/\/LICENSE$/);
  const site = blocks.find((b) => b["@type"] === "WebSite");
  expect(site).toEqual(expect.objectContaining({ name: "Irrevon" }));
  expect(JSON.stringify(site)).not.toContain("SearchAction");
  expect(JSON.stringify(site)).not.toContain("potentialAction");
});

test("JSON-LD: no fabricated offers/ratings/reviews/organization on any page", async ({ page }) => {
  for (const path of PAGES) {
    await page.goto(path);
    const raw = await page
      .locator("script[type='application/ld+json']")
      .evaluateAll((els) => els.map((e) => e.textContent ?? "").join("\n"));
    for (const banned of ["aggregateRating", '"offers"', '"review"', '"Organization"']) {
      expect(raw, `${path} carries fabricated structured data ${banned}`).not.toContain(banned);
    }
  }
});

test("JSON-LD: research post is an Article with published date", async ({ page }) => {
  await page.goto("/research/preregistering-a-benchmark/");
  const blocks = await page
    .locator("script[type='application/ld+json']")
    .evaluateAll((els) => els.map((e) => JSON.parse(e.textContent ?? "{}")));
  const art = blocks.find((b) => b["@type"] === "Article");
  expect(art).toBeTruthy();
  expect(art!.datePublished).toMatch(/^\d{4}-\d{2}-\d{2}$/);
  await expect(page.locator("meta[property='article:published_time']")).toHaveCount(1);
});

test("JSON-LD: docs pages carry TechArticle + BreadcrumbList", async ({ page }) => {
  await page.goto("/docs/reference/rfc-002/");
  const blocks = await page
    .locator("script[type='application/ld+json']")
    .evaluateAll((els) => els.map((e) => JSON.parse(e.textContent ?? "{}")));
  expect(blocks.map((b) => b["@type"])).toEqual(expect.arrayContaining(["TechArticle", "BreadcrumbList"]));
});
