import { spawn, type ChildProcess } from "node:child_process";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/**
 * THE joint proof (`make web-e2e-live`): real `irrevon demo --keep` data,
 * real `irrevon serve`, the packaged workbench served by the engine itself
 * (src/irrevon/_web — staged by `make web-build dist-stage`, ADR-0018
 * mechanics), driven by Playwright:
 *
 *  1. version handshake: Irrevon-Schema-Version header + payload
 *     schema_version on every API response
 *  2. served bundle carries no fixture sentinel and no MSW worker
 *     (sentinel-zero scan of the staged assets on disk)
 *  3. connected: real flagship data renders with the LIVE chip, no MSW
 *  4. SIGKILL-disconnect: killing the engine flips the banner; rendered
 *     data stays; nothing falls back to fixtures
 *
 * The version-999 refusal is covered by the stub suite
 * (e2e/workflows/live-serve.spec.ts) — real serve always speaks version 1.
 *
 * Prerequisites (the `web-e2e-live` make target provides them): test
 * Postgres up (`make py-db-up`), workbench staged (`make web-build
 * dist-stage`), uv available at the repo root.
 */

// One worker, in order: the suite owns the engine process; the SIGKILL
// test is last and terminal.
test.describe.configure({ mode: "serial" });

const WEB_ROOT = join(import.meta.dirname, "../..");
const REPO_ROOT = join(WEB_ROOT, "..");
const STAGED = join(REPO_ROOT, "src/irrevon/_web");

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

// Fixture-only values that must NOT exist in any served bundle asset. The
// flagship id itself is REAL data here (it arrives over the API), so the
// scan targets the bundle files, never the API payloads.
const SENTINELS = [
  FLAGSHIP,
  "dest_5243b02b710b9e0def33cb9e6eddc48e",
  "acme-store/prod",
  "Synthetic fixture — not live or measured",
];

let engine: ChildProcess | null = null;
let origin = "";

function startEngine(): Promise<string> {
  return new Promise((resolve, reject) => {
    // live_server execv's into `irrevon serve`, so this pid IS the engine —
    // SIGKILLing it later is the real crash, not a wrapper kill.
    const proc = spawn("uv", ["run", "python", "tests/serve/live_server.py"], {
      cwd: REPO_ROOT,
      env: { ...process.env },
      stdio: ["ignore", "pipe", "inherit"],
    });
    engine = proc;
    proc.once("error", reject);
    proc.once("exit", (code) => {
      if (!origin) reject(new Error(`live_server exited ${code} before ready`));
    });
    let buffer = "";
    proc.stdout.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      const line = buffer.split("\n").find((l) => l.includes('"url"'));
      if (line) {
        const ready = JSON.parse(line) as { url: string; schema_version: string };
        expect(ready.schema_version).toBe("1");
        resolve(ready.url.replace(/\/$/, ""));
      }
    });
  });
}

test.beforeAll(async () => {
  expect(
    existsSync(join(STAGED, "index.html")),
    "staged workbench missing — run `make web-build dist-stage` (the make target does)",
  ).toBe(true);
  // The demo leg (real SIGKILL + recovery) runs before serve comes up.
  test.setTimeout(360_000);
  origin = await startEngine();
});

test.afterAll(async () => {
  if (engine?.exitCode === null && engine.signalCode === null) {
    engine.kill("SIGTERM");
    await new Promise((r) => engine?.once("exit", r));
  }
});

test("version handshake: header + payload schema_version on every response", async ({
  request,
}) => {
  const health = await request.get(`${origin}/api/v1/health`);
  expect(health.status()).toBe(200);
  expect(health.headers()["irrevon-schema-version"]).toBe("1");
  const body = (await health.json()) as Record<string, unknown>;
  expect(body.schema_version).toBe("1");

  // Errors carry the handshake too.
  const missing = await request.get(`${origin}/api/v1/effects/${"f".repeat(64)}`);
  expect(missing.status()).toBe(404);
  expect(missing.headers()["irrevon-schema-version"]).toBe("1");
});

test("served bundle: no fixture sentinel, no MSW worker (sentinel-zero scan)", () => {
  expect(existsSync(join(STAGED, "mockServiceWorker.js"))).toBe(false);
  const assetsDir = join(STAGED, "assets");
  const assets = readdirSync(assetsDir);
  expect(assets.some((name) => name.startsWith("browser-"))).toBe(false);
  for (const asset of assets) {
    const content = readFileSync(join(assetsDir, asset), "utf8");
    for (const sentinel of SENTINELS) {
      expect(content.includes(sentinel), `${asset} contains "${sentinel.slice(0, 24)}…"`).toBe(
        false,
      );
    }
  }
});

test("connected: real flagship data renders with the LIVE chip, no MSW", async ({
  browser,
}) => {
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  const workerRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("mockServiceWorker")) workerRequests.push(request.url());
  });
  try {
    await page.goto(`${origin}/effects`);
    await expect(page.getByRole("heading", { name: "Effects" })).toBeVisible();

    const chip = page.getByTestId("live-chip");
    await expect(chip).toBeVisible();
    await expect(chip).toHaveAttribute("data-state", "connected", { timeout: 30_000 });

    // The REAL flagship effect (demo seed 42) is reachable by deep link —
    // data proven to come from the engine, not any bundle content (the
    // sentinel scan above proved the id is absent from the bundle).
    await page.goto(`${origin}/effects/${FLAGSHIP}`);
    await expect(page.getByText(FLAGSHIP.slice(0, 8), { exact: false }).first()).toBeVisible({
      timeout: 15_000,
    });

    await expect(page.getByText("Synthetic fixture — not live or measured")).toHaveCount(0);
    await expect(page.getByTestId("disconnected-banner")).toHaveCount(0);
    expect(workerRequests, "no MSW worker request in live mode").toEqual([]);
    const registrations = await page.evaluate(async () => {
      const regs = await navigator.serviceWorker.getRegistrations();
      return regs.length;
    });
    expect(registrations, "no service worker in a live build").toBe(0);
  } finally {
    await context.close();
  }
});

test("SIGKILL-disconnect: banner flips, data stays, no fixture fallback", async ({
  browser,
}) => {
  // The banner flips on the NEXT health poll: 15 s interval + one retry —
  // the honest interval is not shortened for the test.
  test.setTimeout(120_000);
  const context = await browser.newContext({ baseURL: origin });
  const page = await context.newPage();
  try {
    await page.goto(`${origin}/effects`);
    await expect(page.getByTestId("live-chip")).toHaveAttribute("data-state", "connected", {
      timeout: 30_000,
    });
    const rows = page.getByRole("row");
    const rowCount = await rows.count();
    expect(rowCount).toBeGreaterThan(1); // header + at least one data row

    // The real crash: SIGKILL the engine process mid-session.
    engine?.kill("SIGKILL");
    await new Promise((r) => engine?.once("exit", r));

    const banner = page.getByTestId("disconnected-banner");
    await expect(banner).toBeVisible({ timeout: 60_000 });
    await expect(banner).toContainText("Engine unreachable — data may be stale");

    // Already-rendered rows stay (stale-marked); no fixture content appears.
    expect(await rows.count()).toBe(rowCount);
    await expect(page.getByText("Synthetic fixture — not live or measured")).toHaveCount(0);
    await expect(page.getByTestId("live-chip")).toHaveAttribute("data-state", "disconnected");

    const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations).toEqual([]);
  } finally {
    await context.close();
  }
});
