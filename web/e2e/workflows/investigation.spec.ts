import { expect, test } from "@playwright/test";

/**
 * The effect-investigation workflow against the truth fixtures (captured from
 * the real engine at the pinned commit; see fixtures/canonical/provenance.json).
 */

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";

test.describe("effects grid", () => {
  test("renders the seven truth-fixture rows with three status columns", async ({ page }) => {
    await page.goto("/effects");
    const grid = page.getByRole("grid", { name: "Effects" });
    await expect(grid.locator("tbody tr")).toHaveCount(7);
    for (const column of ["Lifecycle", "Reconciliation", "Resolution"]) {
      await expect(grid.getByRole("columnheader", { name: column })).toBeVisible();
    }
    // The duplicate row carries its schema-derived destination-effect count.
    await expect(page.getByText("DUPLICATE ×2")).toBeVisible();
    // No sort affordance exists: ordering beyond the cursor contract is not contracted.
    await expect(grid.locator("th button")).toHaveCount(0);
  });

  test("URL-backed lifecycle filter narrows exactly", async ({ page }) => {
    await page.goto("/effects?lifecycle=AMBIGUOUS");
    const grid = page.getByRole("grid", { name: "Effects" });
    await expect(grid.locator("tbody tr")).toHaveCount(1);
    await expect(grid.getByText("subscription.cancel")).toBeVisible();

    await page.getByRole("button", { name: "Clear filters" }).click();
    await expect(grid.locator("tbody tr")).toHaveCount(7);
    await expect(page).not.toHaveURL(/lifecycle/);
  });

  test("filter-empty state preserves filters and offers clearing", async ({ page }) => {
    await page.goto("/effects?lifecycle=CANCELLED");
    await expect(page.getByText("No effects match these filters.")).toBeVisible();
    // The filter survives in the URL (the router JSON-encodes array params).
    await expect(page).toHaveURL(/lifecycle=.*CANCELLED/);
    await page.getByRole("button", { name: "Clear filters" }).first().click();
    await expect(page.getByRole("grid", { name: "Effects" }).locator("tbody tr")).toHaveCount(
      7,
    );
  });

  test("grid keyboard model: roving focus, j/k, Enter opens detail", async ({ page }) => {
    await page.goto("/effects");
    const grid = page.getByRole("grid", { name: "Effects" });
    await grid.locator("tbody tr").first().waitFor();

    // Exactly one tabbable descendant (roving tabindex).
    await expect(grid.locator('[tabindex="0"]')).toHaveCount(1);

    await grid.locator("tbody tr").first().focus();
    await page.keyboard.press("j");
    await expect(grid.locator("tbody tr").nth(1)).toBeFocused();
    await page.keyboard.press("k");
    await expect(grid.locator("tbody tr").nth(0)).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await page.keyboard.press("ArrowDown");
    await expect(grid.locator("tbody tr").nth(2)).toBeFocused();

    // Cell navigation enters and leaves without breaking the single tab stop.
    await page.keyboard.press("ArrowRight");
    await expect(grid.locator('[data-grid-cell="2:0"]')).toBeFocused();
    await expect(grid.locator('[tabindex="0"]')).toHaveCount(1);
    await page.keyboard.press("ArrowLeft");
    await expect(grid.locator("tbody tr").nth(2)).toBeFocused();

    // Enter docks the row inspector at desktop widths; `o` opens detail.
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/inspect=[0-9a-f]{64}/);
    await page.keyboard.press("o");
    await expect(page).toHaveURL(/\/effects\/[0-9a-f]{64}$/);
  });

  test("c copies the focused effect id and announces politely", async ({ page }) => {
    await page.goto("/effects");
    const grid = page.getByRole("grid", { name: "Effects" });
    await grid.locator("tbody tr").first().focus();
    await page.keyboard.press("c");
    await expect(page.getByRole("status")).toContainText("Effect ID copied");
  });

  test("/ focuses the filter input from the grid", async ({ page }) => {
    await page.goto("/effects");
    const grid = page.getByRole("grid", { name: "Effects" });
    await grid.locator("tbody tr").first().focus();
    await page.keyboard.press("/");
    await expect(page.getByPlaceholder(/exact, e\.g\./)).toBeFocused();
  });
});

test.describe("effect detail — the flagship investigation", () => {
  test("header carries identity, triplet, and copy control", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    // Title block: source-derived title; the full id sits behind a disclosure.
    await expect(
      page.getByRole("heading", { name: "order.create · acme-store/prod" }),
    ).toBeVisible();
    await page.getByText("Full effect id").click();
    await expect(page.getByText(FLAGSHIP, { exact: true }).first()).toBeVisible();
    await expect(page.getByText("Lifecycle: settled committed").first()).toBeAttached();
    await expect(page.getByText("Reconciliation: confirmed unique").first()).toBeAttached();
    await expect(page.getByText("Resolution: closed").first()).toBeAttached();
    await expect(page.getByRole("button", { name: "Copy effect id" })).toBeVisible();
    // Read-only surface: no mutating affordance exists.
    for (const verb of ["Resolve", "Retry", "Redispatch", "Cancel", "Rollback"]) {
      await expect(page.getByRole("button", { name: verb })).toHaveCount(0);
    }
  });

  test("timeline shows the ratchet boundary and the crash/restart seam", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    await expect(
      page.getByText("Externalized — cannot be recalled, only reconciled or compensated."),
    ).toBeVisible();
    await expect(page.getByText("process crash · restart — recovery replay")).toBeVisible();
    // Post-dispatch copy carries no rollback/undo language.
    const timeline = page.getByRole("list", { name: "" }).first();
    void timeline;
    const body = await page.locator("main").innerText();
    expect(body.toLowerCase()).not.toContain("undo");
    expect(body.toLowerCase()).not.toContain("rollback");
  });

  test("decision log shows the exact dedup denial with cited evidence", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    await expect(page.getByText("decision 2 [dispatch]")).toBeVisible();
    await expect(page.getByText("dedup: denied")).toBeVisible();
    await expect(page.getByText(/cause duplicate_intent/)).toBeVisible();
    await expect(page.getByText(/cites execution/)).toBeVisible();
  });

  test("re-synthesis exhibit: identity convergence over digest divergence", async ({
    page,
  }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    await expect(page.getByText("identity — convergent")).toBeVisible();
    await expect(page.getByText("parameters — divergent (non-identity)")).toBeVisible();
    // Digest-only: the exhibit shows digests, never reconstructed payload text.
    const exhibit = page.locator("section", {
      has: page.getByRole("heading", { name: "Re-synthesis exhibit" }),
    });
    await expect(exhibit.getByText(/sha256:/).first()).toBeVisible();
    await expect(exhibit.getByText("loading dock")).toHaveCount(0);
  });

  test("digest-first evidence: raw JSON is collapsed behind disclosure", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    const summary = page.getByText(/Show exact JSON/);
    await expect(summary).toBeVisible();
    await expect(page.locator("pre")).not.toBeVisible();
    await summary.click();
    await expect(page.locator("pre")).toBeVisible();
  });

  test("not-found id preserves the entered value and does not guess", async ({ page }) => {
    const missing = "f".repeat(64);
    await page.goto(`/effects/${missing}`);
    await expect(page.getByRole("heading", { name: "No exact match" })).toBeVisible();
    await expect(page.getByText(missing)).toBeVisible();
  });
});

test.describe("demo playback", () => {
  test("steps through the recorded artifact; contrast summary is artifact-only", async ({
    page,
  }) => {
    await page.goto("/demo");
    await expect(page.getByText("1 / 11")).toBeVisible();
    await expect(
      page.getByText("Intent registered, persisted before dispatch", { exact: true }),
    ).toBeVisible();

    const next = page.getByRole("button", { name: "Next →" });
    for (let i = 0; i < 10; i += 1) {
      await next.click();
    }
    await expect(page.getByText("11 / 11")).toBeVisible();
    await expect(next).toBeDisabled();

    // The B5 leg is present and distinct.
    await expect(page.getByText("B5 restarts from its durable journal")).toBeVisible();
    // The contrast table shows artifact numbers only.
    const summary = page.getByRole("region", { name: "Contrast result" });
    await expect(summary.getByText("contrast_holds: true")).toBeVisible();
    await expect(summary.getByRole("cell", { name: "1", exact: true })).toBeVisible();
    await expect(summary.getByRole("cell", { name: "2", exact: true })).toBeVisible();

    // Handoff: deep link into the retained effect, preserving a graph node.
    await page.getByRole("link", { name: /Inspect the retained effect/ }).click();
    await expect(page).toHaveURL(new RegExp(`/effects/${FLAGSHIP}`));
    await expect(page).toHaveURL(/selected=/);
  });

  test("previous and restart controls work; no autoplay on load", async ({ page }) => {
    await page.goto("/demo");
    await expect(page.getByText("1 / 11")).toBeVisible();
    // Still on step 1 after a beat — no autoplay.
    await page.waitForTimeout(600);
    await expect(page.getByText("1 / 11")).toBeVisible();
    await page.getByRole("button", { name: "Next →" }).click();
    await page.getByRole("button", { name: "← Previous" }).click();
    await expect(page.getByText("1 / 11")).toBeVisible();
  });
});

test.describe("findings and health", () => {
  test("orphan finding is destination-keyed with no effect link", async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 });
    await page.goto("/findings");
    const orphanRow = page.locator("tr", { hasText: "ORPHANED" });
    await expect(orphanRow.getByText("destination-keyed — no ledger record")).toBeVisible();
    await expect(orphanRow.getByRole("link")).toHaveCount(0);
    // Ledger-keyed findings link to their effect from the inspector.
    const lostRow = page.locator("tr", { hasText: "LOST" });
    await lostRow.click();
    const inspector = page.locator('[data-testid="finding-inspector"]:visible');
    await expect(inspector.locator('a[href^="/effects/"]')).toHaveCount(1);
    // The orphan inspector has no effect link at all.
    await page.locator("tr", { hasText: "ORPHANED" }).click();
    await expect(inspector.locator('a[href^="/effects/"]')).toHaveCount(0);
  });

  test("health renders the doctor transcript verbatim", async ({ page }) => {
    await page.goto("/health");
    await expect(page.getByText("identity_selftest")).toBeVisible();
    await expect(page.getByText("pinned vectors reproduce byte-for-byte")).toBeVisible();
    await expect(page.getByText("ledger_db")).toBeVisible();
  });

  test("adapters render the real capability declaration", async ({ page }) => {
    await page.goto("/adapters");
    await expect(page.getByRole("heading", { name: "refdest-c2" })).toBeVisible();
    await expect(
      page.getByText("not supported — recorded as a passing expected negative contract test"),
    ).toBeVisible();
    await expect(page.getByText("Capability tier C2: queryable")).toBeAttached();
  });
});
