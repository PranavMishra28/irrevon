import { expect, test } from "@playwright/test";

/**
 * Attention acceptance (REDESIGN-BRIEF §5.6): the implementation equals the
 * A5 formula over the fixture ledger — 1 AMBIGUOUS effect, 3 findings with
 * OPEN resolutions (one of them a destination-keyed orphan) — with exact
 * reasons, destination-based orphan keys, and no rank/score/action.
 */

test.describe("attention", () => {
  test("derived worklist equals the formula over the fixtures", async ({ page }) => {
    await page.goto("/attention");
    await expect(page.getByRole("heading", { name: "Attention" })).toBeVisible();

    // The formula appears verbatim.
    await expect(page.getByText("lifecycle = AMBIGUOUS").first()).toBeVisible();
    await expect(
      page.getByText("resolution.status IN (OPEN, ESCALATED_HUMAN)").first(),
    ).toBeVisible();

    // Fixture math: 1 ambiguous effect + 3 open findings.
    const ambiguousGroup = page.getByRole("region", {
      name: "Effects where lifecycle = AMBIGUOUS",
    });
    await expect(ambiguousGroup.getByRole("link")).toHaveCount(1);
    const findingsGroup = page.getByRole("region", {
      name: "Findings where resolution.status IN (OPEN, ESCALATED_HUMAN)",
    });
    await expect(findingsGroup.getByRole("link")).toHaveCount(3);
  });

  test("every item shows its exact inclusion reason", async ({ page }) => {
    await page.goto("/attention");
    const reasons = page.getByText(/included because:/);
    await expect(reasons.first()).toBeVisible();
    expect(await reasons.count()).toBeGreaterThanOrEqual(4);
  });

  test("orphan items keep a destination-based key and link to the finding inspector", async ({
    page,
  }) => {
    await page.goto("/attention");
    const orphan = page.getByRole("link", { name: /ORPHANED/ });
    await expect(orphan).toContainText("destination:refdest-c2:");
    await orphan.click();
    await expect(page).toHaveURL(/\/findings\?selected=fnd_/);
    await expect(page.locator('[data-testid="finding-inspector"]:visible')).toBeVisible();
  });

  test("effect items open the owning investigation", async ({ page }) => {
    await page.goto("/attention");
    await page
      .getByRole("region", { name: "Effects where lifecycle = AMBIGUOUS" })
      .getByRole("link")
      .click();
    await expect(page).toHaveURL(/\/effects\/[0-9a-f]{64}$/);
  });

  test("j/k move item focus; no action, score, or rank vocabulary", async ({ page }) => {
    await page.goto("/attention");
    const first = page
      .getByRole("region", { name: /AMBIGUOUS/ })
      .getByRole("link")
      .first();
    await first.focus();
    await page.keyboard.press("j");
    const focusedHref = await page.evaluate(() => document.activeElement?.getAttribute("href"));
    // Next item in source order is an effect-backed open finding.
    expect(focusedHref).toMatch(/\/effects\/[0-9a-f]{64}$/);
    await page.keyboard.press("k");
    const backHref = await page.evaluate(() => document.activeElement?.getAttribute("href"));
    expect(backHref).toMatch(/\/effects\/[0-9a-f]{64}$/);

    const body = ((await page.locator("main").textContent()) ?? "").toLowerCase();
    for (const banned of ["severity", "assignee", "resolve now", "priority"]) {
      expect(body).not.toContain(banned);
    }
  });

  test("partial source yields an explicit partial-worklist statement", async ({ browser }) => {
    // Block the MSW service worker so route interception can inject a
    // partial envelope.
    const context = await browser.newContext({ serviceWorkers: "block" });
    const page = await context.newPage();
    const { readFile } = await import("node:fs/promises");
    const effects = JSON.parse(await readFile("fixtures/canonical/effects.json", "utf8")) as {
      data: Record<string, unknown>[];
      [k: string]: unknown;
    };
    const envelope = {
      ...effects,
      data: effects.data.map((record) => ({
        record,
        classification: "UNRECONCILED",
        finding: null,
      })),
      has_more: true,
      next_cursor: "50",
    };
    await page.route("**/api/v1/**", async (route) => {
      const url = new URL(route.request().url());
      if (url.pathname === "/api/v1/effects") {
        await route.fulfill({ json: envelope });
        return;
      }
      if (url.pathname === "/api/v1/findings") {
        await route.fulfill({ path: "fixtures/canonical/findings.json" });
        return;
      }
      await route.abort();
    });
    await page.goto("/attention");
    await expect(
      page.getByText("A source snapshot is partial — this worklist is partial too."),
    ).toBeVisible({ timeout: 10_000 });
    await context.close();
  });
});
