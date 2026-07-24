import { readFile } from "node:fs/promises";
import { expect, test } from "@playwright/test";

/** The Q1 read returns {record, classification, finding} items; the raw
 * fixture stores bare records — reshape it the way the MSW handler does. */
async function q1Envelope(): Promise<Record<string, unknown>> {
  const effects = JSON.parse(await readFile("fixtures/canonical/effects.json", "utf8")) as {
    data: Record<string, unknown>[];
    [k: string]: unknown;
  };
  return {
    ...effects,
    data: effects.data.map((record) => ({
      record,
      classification: "UNRECONCILED",
      finding: null,
    })),
  };
}

/**
 * Overview acceptance (REDESIGN-BRIEF §5.2): complete-snapshot counts that
 * reconcile with the served fixture, explicit refusals for partial/error
 * sources, only contracted fields, and no trend/rate/score language.
 */

test.describe("overview", () => {
  test("grouped totals equal loaded records (7 effects, complete snapshot)", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();

    const lifecyclePanel = page
      .getByRole("region", { name: "Effects by lifecycle" })
      .or(page.locator("section", { hasText: "Effects by lifecycle" }).first());
    await expect(lifecyclePanel.getByText("7 recorded")).toBeVisible();

    // The lifecycle rows sum to the loaded total.
    const counts = await page
      .locator("section", { hasText: "Effects by lifecycle" })
      .first()
      .locator("ul li span.tabular")
      .allTextContents();
    const sum = counts.reduce((total, text) => total + Number(text), 0);
    expect(sum).toBe(7);
  });

  test("shows per-source as_of and latest observed as_of as their maximum", async ({
    page,
  }) => {
    await page.goto("/");
    const bar = page.getByRole("region", { name: "Data sources and freshness" });
    await expect(bar.getByText("effects as_of")).toBeVisible();
    await expect(bar.getByText("findings as_of")).toBeVisible();
    await expect(bar.getByText("adapters as_of")).toBeVisible();
    await expect(bar.getByText("latest observed as_of")).toBeVisible();
    await expect(bar.getByText("maximum of the source values above")).toBeVisible();
  });

  test("doctor summary counts equal the transcript; explicitly not live telemetry", async ({
    page,
  }) => {
    await page.goto("/");
    const doctor = page.locator("section", { hasText: "Doctor transcript" }).first();
    await expect(doctor.getByText("7 checks")).toBeVisible();
    await expect(doctor.getByText("not live telemetry")).toBeVisible();
  });

  test("module error is a stated failure, never a zero", async ({ browser }) => {
    // The MSW service worker answers before page.route can; block it so the
    // fault injection below actually reaches the module.
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    const effectsEnvelope = await q1Envelope();
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === "/api/v1/findings") {
        await route.abort();
        return;
      }
      if (url.pathname === "/api/v1/effects") {
        await route.fulfill({ json: effectsEnvelope });
        return;
      }
      const fixture = {
        "/api/v1/adapters": "adapters.json",
        "/api/v1/health": "health.json",
      }[url.pathname];
      if (fixture) {
        await route.fulfill({ path: `fixtures/canonical/${fixture}` });
        return;
      }
      await route.abort();
    });
    await page.goto("/");
    const module = page.locator("section", { hasText: "Finding resolutions" }).last();
    await expect(module.getByText("Source unavailable")).toBeVisible({ timeout: 10_000 });
    await expect(module.getByText("an error is not zero")).toBeVisible();
    // The effects modules still count — one failed source poisons nothing else.
    await expect(page.getByText("7 recorded").first()).toBeVisible();
    await context.close();
  });

  test("architecture diagram is permanently labeled conceptual with a prose twin", async ({
    page,
  }) => {
    await page.goto("/");
    const architecture = page.locator("section", { hasText: "Architecture" }).first();
    await expect(architecture.getByText("CONCEPTUAL — NOT FIXTURE DATA").first()).toBeVisible();
    await expect(architecture.getByText("Registrar").last()).toBeVisible();
    await expect(architecture.getByText("append-only record")).toBeVisible();
  });

  test("no trend, rate, or score language anywhere on the page", async ({ page }) => {
    await page.goto("/");
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await expect(page.locator('[aria-busy="true"]')).toHaveCount(0);
    const body = (await page.locator("main").textContent()) ?? "";
    for (const banned of ["trend", "% ", "uptime", "latency", "score", "all safe"]) {
      expect(body.toLowerCase()).not.toContain(banned);
    }
  });

  test("bench readiness pointer discloses developmental pilots and links to /bench", async ({
    page,
  }) => {
    await page.goto("/");
    await expect(
      page.getByText(/Developmental S-REF pilots are non-confirmatory mechanism evidence/),
    ).toBeVisible();
    await page.getByRole("link", { name: /Benchmark readiness and prerequisites/ }).click();
    await expect(page).toHaveURL(/\/bench$/);
  });
});
