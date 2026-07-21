import { execFileSync } from "node:child_process";
import { createServer, type Server } from "node:http";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, extname } from "node:path";
import { expect, test } from "@playwright/test";

/**
 * Future-live guard (REDESIGN-BRIEF §7.3): a live-mode artifact built with
 * no server behind it must fail visibly — no fixture banner, no fixture
 * rows, no MSW worker, and no canonical fixture sentinel anywhere in the
 * build output. A failed live read can never fall back to fixtures.
 */

// One worker, in order: the suite builds artifacts and owns a port.
test.describe.configure({ mode: "serial" });

const WEB_ROOT = join(import.meta.dirname, "../..");
const LIVE_DIST = join(WEB_ROOT, "dist-live-guard");
const PORT = 5198;

const MIME: Record<string, string> = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".json": "application/json",
};

let server: Server | null = null;

test.beforeAll(() => {
  // Build a real production live artifact into a scratch dir (no MSW).
  execFileSync("pnpm", ["exec", "vite", "build", "--outDir", "dist-live-guard"], {
    cwd: WEB_ROOT,
    env: { ...process.env, VITE_DETENT_DATA_MODE: "live" },
    stdio: "pipe",
  });
  // Serve it statically: every /api/v1/* read 404s — the "no server" world.
  server = createServer((req, res) => {
    const url = new URL(req.url ?? "/", `http://localhost:${PORT}`);
    if (url.pathname.startsWith("/api/")) {
      res.writeHead(404, { "content-type": "application/json" });
      res.end(JSON.stringify({ error: "not_found" }));
      return;
    }
    let filePath = join(LIVE_DIST, url.pathname);
    if (!existsSync(filePath) || url.pathname === "/") {
      filePath = join(LIVE_DIST, "index.html");
    }
    try {
      const body = readFileSync(filePath);
      res.writeHead(200, {
        "content-type": MIME[extname(filePath)] ?? "application/octet-stream",
      });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end();
    }
  }).listen(PORT);
});

test.afterAll(() => {
  server?.close();
});

test("live build output carries no fixture sentinel, no MSW worker, no mock banner", () => {
  const assets = readdirSync(join(LIVE_DIST, "assets"));
  expect(assets.some((name) => name.startsWith("browser-"))).toBe(false);
  expect(existsSync(join(LIVE_DIST, "mockServiceWorker.js"))).toBe(false);

  const SENTINELS = [
    // Canonical fixture values that exist ONLY in fixtures/canonical.
    "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5",
    "dest_5243b02b710b9e0def33cb9e6eddc48e",
    "acme-store/prod",
    "Synthetic fixture — not live or measured",
  ];
  for (const asset of assets) {
    const content = readFileSync(join(LIVE_DIST, "assets", asset), "utf8");
    for (const sentinel of SENTINELS) {
      expect(content.includes(sentinel), `${asset} contains "${sentinel.slice(0, 24)}…"`).toBe(
        false,
      );
    }
  }
});

test("failed live reads surface disconnected truth — never fixtures", async ({ browser }) => {
  const context = await browser.newContext({ baseURL: `http://localhost:${PORT}` });
  const page = await context.newPage();
  const workerRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("mockServiceWorker")) workerRequests.push(request.url());
  });

  await page.goto(`http://localhost:${PORT}/effects`);
  await expect(page.getByRole("heading", { name: "Effects" })).toBeVisible();
  // The read fails visibly (react-query retries once, then errors).
  await expect(page.getByText(/NotFoundError|TransportError|Read failed/).first()).toBeVisible({
    timeout: 15_000,
  });
  // No fixture banner, no fixture rows, no fixture ids.
  await expect(page.getByText("Synthetic fixture — not live or measured")).toHaveCount(0);
  await expect(page.getByText("subscription.cancel")).toHaveCount(0);
  expect(workerRequests, "no MSW worker request in live mode").toEqual([]);

  // Health states the live mode honestly.
  await page.goto(`http://localhost:${PORT}/health`);
  await expect(page.getByText("Doctor unavailable")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("live", { exact: true }).first()).toBeVisible();

  const registrations = await page.evaluate(async () => {
    const regs = await navigator.serviceWorker.getRegistrations();
    return regs.length;
  });
  expect(registrations, "no service worker in a live build").toBe(0);
  await context.close();
});

test("a production build in mock mode is refused outright", () => {
  let failed = false;
  try {
    execFileSync("pnpm", ["exec", "vite", "build", "--outDir", "dist-mock-refused"], {
      cwd: WEB_ROOT,
      env: { ...process.env, VITE_DETENT_DATA_MODE: "mock" },
      stdio: "pipe",
    });
  } catch (error) {
    failed = true;
    expect(String((error as { stderr?: Buffer }).stderr ?? "")).toContain("Refusing to build");
  }
  expect(failed, "mock production build must fail").toBe(true);
});
