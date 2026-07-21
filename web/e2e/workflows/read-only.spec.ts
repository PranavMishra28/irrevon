import { expect, test } from "@playwright/test";
import type { Page } from "@playwright/test";

/**
 * Read-only / network guarantee (REDESIGN-BRIEF §7.3): across every visible
 * route and the main workflows, (1) no request leaves loopback, and (2) the
 * workbench issues only GET/HEAD — no mutating method ever, from anywhere.
 */

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";

const ROUTES = [
  "/",
  "/effects",
  `/effects?inspect=${FLAGSHIP}`,
  `/effects/${FLAGSHIP}`,
  `/effects/${FLAGSHIP}?selected=node:attempt:1`,
  "/findings?selected=fnd_00000000000000000004",
  "/attention",
  "/adapters",
  "/demo?step=10",
  "/bench",
  "/learn/start",
  "/learn/identity",
  "/learn/state",
  "/learn/tiers",
  "/health",
  "/taxonomy",
];

function watch(page: Page) {
  const external: string[] = [];
  const mutating: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
      external.push(`${request.method()} ${url.href}`);
    }
    if (!["GET", "HEAD"].includes(request.method())) {
      mutating.push(`${request.method()} ${url.href}`);
    }
  });
  return { external, mutating };
}

test("every route: zero non-loopback requests, zero non-GET/HEAD methods", async ({ page }) => {
  const { external, mutating } = watch(page);
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
      await route.abort();
      return;
    }
    await route.continue();
  });
  for (const path of ROUTES) {
    await page.goto(path);
    await expect(page.getByRole("heading", { level: 1 }).first()).toBeVisible();
    await page.waitForLoadState("networkidle");
  }
  expect(external, "non-loopback requests").toEqual([]);
  expect(mutating, "mutating request methods").toEqual([]);
});

test("main workflows: filters, selection, drawers, graph, playback, theme, palette, copy", async ({
  page,
  context,
}) => {
  await context.grantPermissions(["clipboard-read", "clipboard-write"]);
  const { external, mutating } = watch(page);

  // Effects: filter, inspect, copy.
  await page.goto("/effects");
  await page.getByRole("button", { name: "AMBIGUOUS", exact: true }).click();
  await page.getByRole("button", { name: "Clear filters" }).click();
  const grid = page.getByRole("grid", { name: "Effects" });
  await grid.locator("tbody tr").first().focus();
  await page.keyboard.press("c");
  await page.keyboard.press("Enter");
  await expect(page.getByTestId("effect-row-inspector")).toBeVisible();

  // Investigation: graph selection + timeline sync.
  await page.goto(`/effects/${FLAGSHIP}`);
  await page.getByTestId("causal-graph").locator('[data-graph-node-index="0"]').click();
  await expect(page.getByTestId("graph-inspector")).toBeVisible();

  // Findings selection; Attention; Adapters; Health; Bench.
  await page.goto("/findings");
  await page.getByRole("table", { name: "Findings" }).locator("tbody tr").first().click();
  await page.goto("/attention");
  await page.goto("/adapters");
  await page.goto("/health");
  await page.goto("/bench");

  // Demo playback.
  await page.goto("/demo");
  await page.getByRole("button", { name: "Next →" }).click();
  await page.getByRole("button", { name: "Play" }).click();
  await page.getByRole("button", { name: "Pause" }).click();

  // Theme/density/help/palette.
  await page.getByRole("button", { name: "Switch to dark theme" }).click();
  await page.getByRole("button", { name: /Switch to .* density/ }).click();
  await page.keyboard.press("ControlOrMeta+k");
  await page.getByPlaceholder(/Go to view/).fill("health");
  await page.keyboard.press("Escape");

  // Mobile drawer.
  await page.setViewportSize({ width: 375, height: 812 });
  await page.getByRole("button", { name: "Menu" }).click();
  await page
    .getByRole("dialog", { name: "Menu" })
    .getByRole("link", { name: "Overview" })
    .click();

  await page.waitForLoadState("networkidle");
  expect(external, "non-loopback requests").toEqual([]);
  expect(mutating, "mutating request methods").toEqual([]);
});

test("service worker is the dev-only mock transport; no other worker registers", async ({
  page,
}) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const registrations = await page.evaluate(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    return regs.map((r) => r.active?.scriptURL ?? "pending");
  });
  // The review build runs MSW; nothing else may register.
  for (const url of registrations) {
    expect(url).toContain("mockServiceWorker.js");
  }
});
