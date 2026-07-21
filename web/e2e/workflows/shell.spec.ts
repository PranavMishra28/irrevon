import { expect, test } from "@playwright/test";

import type { Page } from "@playwright/test";

const HEX64 = "c0ffee".padEnd(64, "0");

/** Wait until the shell is interactive (shortcut listeners attached). */
async function gotoShell(page: Page, path: string) {
  await page.goto(path);
  await page.getByRole("button", { name: /Go to…/ }).waitFor();
}

test.describe("shell", () => {
  test("no runtime request leaves loopback", async ({ page }) => {
    const external: string[] = [];
    await page.route("**/*", async (route) => {
      const url = new URL(route.request().url());
      if (!["localhost", "127.0.0.1", "[::1]"].includes(url.hostname)) {
        external.push(url.href);
        await route.abort();
        return;
      }
      await route.continue();
    });
    await page.goto("/");
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(external).toEqual([]);
  });

  test("virgin landing redirects to Start Here", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/learn\/start$/);
    await expect(page.getByRole("heading", { name: "Start here" })).toBeVisible();
  });

  test("fixture banner is permanent in mock builds", async ({ page }) => {
    for (const path of ["/learn/start", "/health", "/bench"]) {
      await page.goto(path);
      await expect(page.getByText("Synthetic fixture — not live or measured")).toBeVisible();
    }
  });

  test("first tab stop is the skip link; skip link moves focus to main", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.keyboard.press("Tab");
    const skip = page.getByRole("link", { name: "Skip to main content" });
    await expect(skip).toBeFocused();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/#main$/);
  });

  test("palette opens with Cmd/Ctrl+K, routes an exact effect id, and Esc restores focus", async ({
    page,
  }) => {
    await gotoShell(page, "/learn/start");
    const goButton = page.getByRole("button", { name: /Go to…/ });
    await goButton.focus();
    await page.keyboard.press("ControlOrMeta+k");
    const input = page.getByPlaceholder(/Go to view/);
    await expect(input).toBeFocused();

    // Esc closes and restores the invoking focus.
    await page.keyboard.press("Escape");
    await expect(goButton).toBeFocused();

    // Exact 64-hex routes to the effect detail path.
    await page.keyboard.press("ControlOrMeta+k");
    await input.fill(HEX64);
    await expect(page.getByText(/Open effect c0ffee/)).toBeVisible();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(new RegExp(`/effects/${HEX64}$`));
  });

  test("palette refuses receipt ids with an honest reason", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.keyboard.press("ControlOrMeta+k");
    await page.getByPlaceholder(/Go to view/).fill("rcpt_01ARZ3NDEKTSV4RRFFQ69G5FAV");
    await expect(page.getByText("no receipt route in v0.1")).toBeVisible();
  });

  test("g-then-key navigation and ? help dialog", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.keyboard.press("g");
    await page.keyboard.press("e");
    await expect(page).toHaveURL(/\/effects$/);

    await page.keyboard.press("Shift+?");
    await expect(page.getByRole("dialog", { name: "Keyboard shortcuts" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).toHaveCount(0);
  });

  test("single-key shortcuts are user-disableable", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.keyboard.press("Shift+?");
    await page.getByRole("checkbox", { name: /Enable single-character shortcuts/ }).uncheck();
    await page.keyboard.press("Escape");
    await page.keyboard.press("g");
    await page.keyboard.press("e");
    await expect(page).toHaveURL(/\/learn\/start$/);
  });

  test("theme and density toggles persist across reload", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await page.getByRole("button", { name: "Switch to dense density" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-density", "dense");
    await page.reload();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    await expect(page.locator("html")).toHaveAttribute("data-density", "dense");
  });

  test("full-page navigation focuses the route heading", async ({ page }) => {
    await gotoShell(page, "/learn/start");
    await page.getByRole("link", { name: "Health" }).click();
    await expect(page.getByRole("heading", { name: "Health" })).toBeFocused();
  });

  test("unknown route preserves the entered path", async ({ page }) => {
    await page.goto("/effects/not-a-real-id-shape/whatever");
    await expect(page.getByRole("heading", { name: "No exact match" })).toBeVisible();
    await expect(page.getByText("/effects/not-a-real-id-shape/whatever")).toBeVisible();
  });

  test("no body horizontal overflow at 1024/1280/1600", async ({ page }) => {
    for (const width of [1024, 1280, 1600]) {
      await page.setViewportSize({ width, height: 800 });
      await page.goto("/learn/start");
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(overflow, `body overflow at ${width}px`).toBe(false);
    }
  });
});
