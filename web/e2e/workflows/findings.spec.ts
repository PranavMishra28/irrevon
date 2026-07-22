import { expect, test } from "@playwright/test";

/**
 * Findings acceptance (REDESIGN-BRIEF §5.5): URL-backed selection round-
 * trips, orphans render the paired subject/absence view with no fake effect
 * link, digest-only evidence never claims verification, and the mobile
 * cards keep every field visible.
 */

test.describe("findings", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("Created is visible at 1440 without scrolling; all six columns render", async ({
    page,
  }) => {
    await page.goto("/findings");
    const table = page.getByRole("table", { name: "Findings" });
    for (const column of [
      "Finding",
      "Subject",
      "Classification",
      "Resolution",
      "Evidence",
      "Created",
    ]) {
      await expect(table.getByRole("columnheader", { name: column })).toBeVisible();
    }
    const createdHeader = table.getByRole("columnheader", { name: "Created" });
    const box = await createdHeader.boundingBox();
    expect(box).not.toBeNull();
    expect((box?.x ?? 0) + (box?.width ?? 0)).toBeLessThanOrEqual(1440);
  });

  test("row selection docks the inspector and round-trips through the URL", async ({
    page,
  }) => {
    await page.goto("/findings");
    await page.getByRole("table", { name: "Findings" }).locator("tbody tr").first().click();
    await expect(page).toHaveURL(/selected=fnd_/);
    await expect(page.locator('[data-testid="finding-inspector"]:visible')).toBeVisible();

    // Reload: selection survives.
    await page.reload();
    await expect(page.locator('[data-testid="finding-inspector"]:visible')).toBeVisible();

    // Escape clears selection and the URL.
    await page.keyboard.press("Escape");
    await expect(page.locator('[data-testid="finding-inspector"]:visible')).toHaveCount(0);
    await expect(page).not.toHaveURL(/selected=/);
  });

  test("orphan shows the paired absence view; no ledger id, no fake effect link", async ({
    page,
  }) => {
    await page.goto("/findings");
    await page.getByRole("row", { name: /destination-keyed/ }).click();
    const inspector = page.locator('[data-testid="finding-inspector"]:visible');
    await expect(inspector).toBeVisible();
    await expect(inspector.getByText("Destination observation")).toBeVisible();
    await expect(inspector.getByText("Absent ledger record")).toBeVisible();
    await expect(inspector.getByText("never intended through Irrevon")).toBeVisible();
    await expect(inspector.locator('a[href^="/effects/"]')).toHaveCount(0);
  });

  test("digest-only evidence never says verified", async ({ page }) => {
    await page.goto("/findings");
    await page.getByRole("table", { name: "Findings" }).locator("tbody tr").first().click();
    const inspector = page.locator('[data-testid="finding-inspector"]:visible');
    await expect(inspector.getByText(/digest-only/).first()).toBeVisible();
    const text = ((await inspector.textContent()) ?? "").toLowerCase();
    expect(text).not.toContain("verified");
  });

  test("stale selected id leaves the route usable and states the absence", async ({ page }) => {
    await page.goto("/findings?selected=fnd_ZZZZZZZZZZZZZZZZZZZZ");
    await expect(page.getByText("requested selection")).toBeVisible();
    await expect(page.locator('[data-testid="finding-inspector"]:visible')).toHaveCount(0);
    await expect(page.getByRole("table", { name: "Findings" })).toBeVisible();
  });

  test("o opens the owning effect only when one exists", async ({ page }) => {
    await page.goto("/findings");
    const rows = page.getByRole("table", { name: "Findings" }).locator("tbody tr");
    await rows.first().focus();
    await page.keyboard.press("o");
    await expect(page).toHaveURL(/\/effects\/[0-9a-f]{64}$/);

    // Orphan: `o` must do nothing.
    await page.goto("/findings");
    await page.getByRole("row", { name: /destination-keyed/ }).focus();
    await page.keyboard.press("o");
    await expect(page).toHaveURL(/\/findings$/);
  });

  test("mobile cards keep every field visible at 375", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/findings");
    const firstCard = page.locator("article").first();
    await expect(firstCard.getByText("Subject", { exact: true })).toBeVisible();
    await expect(firstCard.getByText("Evidence", { exact: true })).toBeVisible();
    await expect(firstCard.getByText("Created", { exact: true })).toBeVisible();
    await expect(firstCard.getByText("Classification", { exact: true })).toBeVisible();
    await expect(firstCard.getByText("Resolution", { exact: true })).toBeVisible();

    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow, "no body horizontal scroll at 375").toBe(false);
  });
});
