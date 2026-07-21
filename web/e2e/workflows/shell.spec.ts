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

  test("/ is the Overview — no redirect; Effects stays one click away", async ({ page }) => {
    await page.goto("/");
    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "Overview" })).toBeVisible();
    await page
      .getByRole("navigation", { name: "Views" })
      .getByRole("link", { name: "Effects" })
      .click();
    await expect(page).toHaveURL(/\/effects$/);
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

test.describe("responsive shell (REDESIGN A6)", () => {
  test("header composition per breakpoint; no collision, no body scroll", async ({ page }) => {
    // Desktop ≥1120: full nav visible, no menu button.
    await page.setViewportSize({ width: 1120, height: 800 });
    await gotoShell(page, "/effects");
    await expect(page.getByRole("navigation", { name: "Views" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Menu" })).toBeHidden();

    // Tablet 768–1119: nav collapses, active-view label + Menu appear.
    await page.setViewportSize({ width: 1119, height: 800 });
    await expect(page.getByRole("navigation", { name: "Views" })).toBeHidden();
    await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
    await expect(page.getByRole("button", { name: /Go to…/ })).toBeVisible();
    await expect(page.getByTestId("active-view-label")).toHaveText("Effects");
    await expect(page.getByTestId("active-view-label")).toBeVisible();

    // Mobile <768: brand + command icon + menu only.
    await page.setViewportSize({ width: 375, height: 800 });
    await expect(page.getByRole("button", { name: "Menu" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Go to…" })).toBeVisible();
    await expect(page.getByTestId("active-view-label")).toBeHidden();

    await gotoShell(page, "/learn/start");
    for (const width of [320, 375, 768, 1119]) {
      await page.setViewportSize({ width, height: 800 });
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
      );
      expect(overflow, `body overflow at ${width}px`).toBe(false);
    }
  });

  test("drawer: initial focus on Close, Tab trapped, Escape returns focus to trigger", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoShell(page, "/learn/start");
    const menu = page.getByRole("button", { name: "Menu" });
    await menu.click();

    const drawer = page.getByRole("dialog", { name: "Menu" });
    await expect(drawer).toBeVisible();
    await expect(page.getByRole("button", { name: "Close menu" })).toBeFocused();

    // Trap check, both directions: Shift+Tab from Close wraps to the last
    // drawer control; Tab from there returns to Close. Focus never lands on
    // a page control behind the overlay.
    await page.keyboard.press("Shift+Tab");
    await expect
      .poll(async () =>
        page.evaluate(() => ({
          inDrawer: Boolean(document.activeElement?.closest('[role="dialog"]')),
          label: document.activeElement?.textContent ?? "",
        })),
      )
      .toEqual({
        inDrawer: true,
        label: expect.stringContaining("Help and keyboard shortcuts"),
      });
    await page.keyboard.press("Tab");
    // Base UI redirects focus off its edge guard asynchronously — poll.
    await expect
      .poll(async () =>
        page.evaluate(() => ({
          inDrawer: Boolean(document.activeElement?.closest('[role="dialog"]')),
          label: document.activeElement?.getAttribute("aria-label") ?? "",
        })),
      )
      .toEqual({ inDrawer: true, label: "Close menu" });

    await page.keyboard.press("Escape");
    await expect(drawer).toHaveCount(0);
    await expect(menu).toBeFocused();
  });

  test("drawer: choosing a route closes it and the route heading takes focus", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoShell(page, "/learn/start");
    await page.getByRole("button", { name: "Menu" }).click();
    const drawer = page.getByRole("dialog", { name: "Menu" });
    await drawer.getByRole("link", { name: "Health" }).click();
    await expect(page).toHaveURL(/\/health$/);
    await expect(drawer).toHaveCount(0);
    await expect(page.getByRole("heading", { name: "Health" })).toBeFocused();
  });

  test("drawer: backdrop click closes without navigation", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoShell(page, "/learn/start");
    await page.getByRole("button", { name: "Menu" }).click();
    await expect(page.getByRole("dialog", { name: "Menu" })).toBeVisible();
    // Click the overlay area left of the drawer.
    await page.mouse.click(10, 400);
    await expect(page.getByRole("dialog", { name: "Menu" })).toHaveCount(0);
    await expect(page).toHaveURL(/\/learn\/start$/);
  });

  test("drawer utilities: theme toggle works from the drawer", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoShell(page, "/learn/start");
    await page.getByRole("button", { name: "Menu" }).click();
    await page.getByRole("button", { name: "Switch to dark theme" }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
  });

  test("drawer nav rows meet the 44px mobile target size", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 800 });
    await gotoShell(page, "/learn/start");
    await page.getByRole("button", { name: "Menu" }).click();
    const drawer = page.getByRole("dialog", { name: "Menu" });
    const boxes = await drawer.getByRole("link").all();
    for (const row of boxes) {
      const box = await row.boundingBox();
      expect(box, "nav row has a box").not.toBeNull();
      expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    }
  });
});
