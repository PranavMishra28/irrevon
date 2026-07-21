import { expect, test } from "@playwright/test";

/**
 * Slice-4 surface acceptance (REDESIGN-BRIEF §5.7–§5.10): adapter topology
 * declaration-vs-observation honesty, demo lanes with URL step state,
 * health transcript layout, and the Bench evidence null.
 */

test.describe("adapters", () => {
  test("conceptual labels persist; adapter→destination is declared, not observed", async ({
    page,
  }) => {
    await page.goto("/adapters");
    await expect(page.getByText("Caller — CONCEPTUAL")).toBeVisible();
    await expect(page.getByText("Irrevon — CONCEPTUAL")).toBeVisible();
    await expect(page.getByText("declared (VF)")).toBeVisible();
    await expect(page.getByText("Dashed adapter→destination means DECLARED")).toBeVisible();
    // No live-health vocabulary anywhere.
    const body = ((await page.locator("main").textContent()) ?? "").toLowerCase();
    for (const banned of ["uptime", "availability", "drift status: ", "healthy"]) {
      expect(body).not.toContain(banned);
    }
  });

  test("375: declaration card precedes the topology in reading order", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/adapters");
    const declaration = page.getByRole("heading", { name: "refdest-c2" });
    const topology = page.getByText("Declared topology");
    await expect(declaration).toBeVisible();
    const declarationBox = await declaration.boundingBox();
    const topologyBox = await topology.boundingBox();
    expect((declarationBox?.y ?? 0) < (topologyBox?.y ?? 0)).toBe(true);
  });
});

test.describe("demo stage", () => {
  test("two lanes share one step; URL step round-trips", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByRole("region", { name: "Irrevon lane" })).toBeVisible();
    await expect(page.getByRole("region", { name: "B5 baseline lane" })).toBeVisible();

    // Scrub straight to the first baseline event.
    await page.getByRole("button", { name: /Go to step 8/ }).click();
    await expect(page).toHaveURL(/step=7/);
    await expect(
      page.getByRole("region", { name: "B5 baseline lane" }).getByText("b5_response_lost"),
    ).toBeVisible();

    await page.reload();
    await expect(page.getByText("8 / 11")).toBeVisible();
  });

  test("keyboard: Left/Right step; Home/End jump; no autoplay", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByText("1 / 11")).toBeVisible();
    await page.getByRole("button", { name: /Go to step 1:/ }).focus();
    await page.keyboard.press("ArrowRight");
    await expect(page.getByText("2 / 11")).toBeVisible();
    await page.keyboard.press("ArrowLeft");
    await expect(page.getByText("1 / 11")).toBeVisible();
    await page.keyboard.press("End");
    await expect(page.getByText("11 / 11")).toBeVisible();
    await page.keyboard.press("Home");
    await expect(page.getByText("1 / 11")).toBeVisible();
  });

  test("375: lane tabs show one lane at a time; controls are 44px", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/demo");
    const tabs = page.getByRole("tablist", { name: "Lanes" });
    await expect(tabs).toBeVisible();
    await tabs.getByRole("tab", { name: "irrevon" }).click();
    await expect(page.getByRole("region", { name: "Irrevon lane" })).toBeVisible();
    await expect(page.getByRole("region", { name: "B5 baseline lane" })).toHaveCount(0);
    await tabs.getByRole("tab", { name: "baseline" }).click();
    await expect(page).toHaveURL(/lane=baseline/);
    await expect(page.getByRole("region", { name: "B5 baseline lane" })).toBeVisible();

    for (const name of ["Play", "← Previous", "Next →", "Restart"]) {
      const box = await page.getByRole("button", { name, exact: true }).boundingBox();
      expect(box?.height ?? 0, `${name} height`).toBeGreaterThanOrEqual(44);
    }
  });

  test("contrast result stays visible at completion on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto("/demo?step=10");
    await expect(page.getByRole("region", { name: "Contrast result" })).toBeVisible();
    await expect(page.getByText("contrast_holds: true")).toBeVisible();
  });
});

test.describe("health", () => {
  test("summary counts equal the transcript; no run-doctor control", async ({ page }) => {
    await page.goto("/health");
    await expect(
      page.locator("section", { hasText: "Doctor checks" }).last().locator("li"),
    ).toHaveCount(7);
    const okCount = page.locator("dl dd").filter({ hasText: /^7$/ });
    await expect(okCount.first()).toBeVisible();
    await expect(page.getByRole("button", { name: /run|doctor/i })).toHaveCount(0);
    await expect(page.getByText("recorded doctor transcript")).toBeVisible();
  });
});

test.describe("bench readiness", () => {
  test("evidence null: no metric, progress, or synthetic comparison", async ({ page }) => {
    await page.goto("/bench");
    await expect(page.getByText("No benchmark runs exist")).toBeVisible();
    await expect(page.getByText("Prerequisites, in order")).toBeVisible();
    await expect(page.getByText("docs/benchmark-preregistration.md")).toBeVisible();
    const body = ((await page.locator("main").textContent()) ?? "").toLowerCase();
    for (const banned of ["% complete", "progress:", "score", "success rate"]) {
      expect(body).not.toContain(banned);
    }
    // No disabled fake controls.
    await expect(page.locator("main button[disabled]")).toHaveCount(0);
  });
});
