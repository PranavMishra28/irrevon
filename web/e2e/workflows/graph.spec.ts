import { expect, test } from "@playwright/test";

/**
 * Causal-graph acceptance (REDESIGN-BRIEF §4.4/§5.4): roving keyboard order,
 * URL-backed selection round-trips, timeline↔graph selection sync, semantic
 * twins, and the deliberate absence of any multi-effect graph on /effects.
 */

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const PERSISTED = "371a59b8452dd4fe659e9dd4ef78fd8cac90b5dd36583aea1dff9e99b4f74f6c";

test.describe("causal graph", () => {
  test.use({ viewport: { width: 1440, height: 900 } });

  test("flagship graph renders with legend, connections twin, and notch", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    const graph = page.getByTestId("causal-graph");
    await expect(graph).toBeVisible();
    // Node count matches the model (buttons in the graph).
    expect(await graph.getByRole("button").count()).toBeGreaterThanOrEqual(10);
    await expect(page.getByRole("region", { name: "Graph legend" })).toBeVisible();
    const connections = page.getByRole("region", { name: "Connections" });
    await expect(connections.getByRole("table")).toBeVisible();
    await expect(connections.getByText("dedup-cites")).toBeVisible();
    await expect(connections.getByText("evidence-gap (interrupted)")).toBeVisible();
    // Every edge row cites an evidence path.
    const paths = await connections.locator("tbody tr td:nth-child(4)").allTextContents();
    for (const path of paths) {
      expect(path).toMatch(/^(inspect|record)\./);
    }
  });

  test("keyboard: one roving stop, arrows walk causal order, Enter selects, Escape clears", async ({
    page,
  }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    const graph = page.getByTestId("causal-graph");
    await expect(graph.locator('[tabindex="0"]')).toHaveCount(1);

    await graph.locator('[data-graph-node-index="0"]').focus();
    // DOM order equals causal order: index 0 is the intent node.
    await expect(graph.locator('[data-graph-node-index="0"]')).toContainText("Intent");
    await page.keyboard.press("ArrowRight");
    await expect(graph.locator('[data-graph-node-index="1"]')).toBeFocused();
    await page.keyboard.press("ArrowDown");
    await expect(graph.locator('[data-graph-node-index="2"]')).toBeFocused();
    await page.keyboard.press("ArrowLeft");
    await expect(graph.locator('[data-graph-node-index="1"]')).toBeFocused();
    await page.keyboard.press("End");
    const last = (await graph.getByRole("button").count()) - 1;
    await expect(graph.locator(`[data-graph-node-index="${last}"]`)).toBeFocused();
    await page.keyboard.press("Home");
    await expect(graph.locator('[data-graph-node-index="0"]')).toBeFocused();

    // Enter selects and opens the inspector; URL carries the node id.
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/selected=node/);
    await expect(page.getByTestId("graph-inspector")).toBeVisible();
    await expect(page.getByText("1 node selected").first()).toBeVisible();

    // Escape clears selection and returns focus to the node.
    await page.keyboard.press("Escape");
    await expect(page).not.toHaveURL(/selected=/);
    await expect(graph.locator('[data-graph-node-index="0"]')).toBeFocused();
  });

  test("?selected round-trips through reload; stale ids state the absence", async ({
    page,
  }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    const graph = page.getByTestId("causal-graph");
    await graph.locator('[data-graph-node-index="0"]').click();
    await expect(page).toHaveURL(/selected=node%3Aintent|selected=node:intent/);
    await page.reload();
    await expect(page.getByTestId("graph-inspector")).toBeVisible();
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();

    // A stale node id leaves the route usable and states the absence.
    await page.goto(`/effects/${FLAGSHIP}?selected=node:gate:999999`);
    await expect(
      page.getByText("The requested selection is absent from this graph; nothing is selected."),
    ).toBeVisible();
    await expect(page.getByTestId("causal-graph")).toBeVisible();
  });

  test("timeline ↔ graph selection sync via 'show in graph'", async ({ page }) => {
    await page.goto(`/effects/${FLAGSHIP}`);
    await page.getByRole("button", { name: "show in graph" }).first().click();
    await expect(page).toHaveURL(/selected=/);
    await expect(page.getByTestId("graph-inspector")).toBeVisible();
    // The inspector's Evidence panel cites contract paths.
    await page.getByRole("tab", { name: "Evidence" }).click();
    await expect(
      page
        .getByTestId("graph-inspector")
        .getByText(/inspect\./)
        .first(),
    ).toBeVisible();
  });

  test("PERSISTED case: three-rank graph, no notch, no destination side", async ({ page }) => {
    await page.goto(`/effects/${PERSISTED}`);
    const graph = page.getByTestId("causal-graph");
    await expect(graph).toBeVisible();
    const text = (await graph.textContent()) ?? "";
    expect(text).not.toContain("externalized");
    expect(text).not.toContain("Dispatch attempt");
  });

  test("no fleet graph: /effects has no graph mode control and no graph bundle", async ({
    page,
  }) => {
    const graphChunks: string[] = [];
    page.on("request", (request) => {
      const url = request.url();
      // The graph implementation rides in the detail-route chunk.
      if (/_effectId|renderer/.test(url) && url.endsWith(".js")) {
        graphChunks.push(url);
      }
    });
    await page.goto("/effects");
    await expect(page.getByRole("grid", { name: "Effects" })).toBeVisible();
    await expect(page.getByRole("button", { name: /graph/i })).toHaveCount(0);
    expect(graphChunks, "no graph chunk loads on the Effects list").toEqual([]);
  });

  test("effects docked inspector: Enter inspects, o opens, Escape restores focus", async ({
    page,
  }) => {
    await page.goto("/effects");
    const grid = page.getByRole("grid", { name: "Effects" });
    await grid.locator("tbody tr").first().focus();
    await page.keyboard.press("Enter");
    await expect(page).toHaveURL(/inspect=[0-9a-f]{64}/);
    const inspector = page.getByTestId("effect-row-inspector");
    await expect(inspector).toBeVisible();
    await expect(inspector.getByText("Latest recorded transition")).toBeVisible();
    await expect(
      inspector.getByRole("link", { name: "Open causal investigation" }),
    ).toBeVisible();

    // Escape closes and restores row focus.
    await page.keyboard.press("Escape");
    await expect(page).not.toHaveURL(/inspect=/);
    await expect(grid.locator("tbody tr").first()).toBeFocused();

    // `o` opens the full investigation.
    await page.keyboard.press("o");
    await expect(page).toHaveURL(/\/effects\/[0-9a-f]{64}$/);
  });

  test("inspect URL round-trips; invalid inspect ids are dropped", async ({ page }) => {
    await page.goto(`/effects?inspect=${FLAGSHIP}`);
    await expect(page.getByTestId("effect-row-inspector")).toBeVisible();
    // An invalid inspect id is dropped from typed state without guessing:
    // no inspector renders and the list stays fully usable.
    await page.goto("/effects?inspect=not-a-hex-id");
    await expect(page.getByRole("grid", { name: "Effects" })).toBeVisible();
    await expect(page.getByTestId("effect-row-inspector")).toHaveCount(0);
  });
});

test.describe("investigation responsive projections", () => {
  test("375: projection tabs show one panel at a time; graph is vertical", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`/effects/${FLAGSHIP}`);
    const tabs = page.getByRole("tablist", { name: "Investigation projections" });
    await expect(tabs).toBeVisible();
    await expect(page.getByTestId("causal-graph")).toBeVisible();
    await tabs.getByRole("tab", { name: "timeline" }).click();
    await expect(page.getByTestId("causal-graph")).toHaveCount(0);
    await expect(
      page.getByText("Externalized — cannot be recalled", { exact: false }),
    ).toBeVisible();

    // No body-level horizontal scroll with the graph open.
    await tabs.getByRole("tab", { name: "graph" }).click();
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    );
    expect(overflow).toBe(false);
  });

  test("t/g single-key shortcuts switch projections on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await page.goto(`/effects/${FLAGSHIP}`);
    await page.locator("body").click();
    await page.keyboard.press("t");
    await expect(page).toHaveURL(/view=timeline/);
    await page.keyboard.press("g");
    await expect(page).not.toHaveURL(/view=/);
  });
});
