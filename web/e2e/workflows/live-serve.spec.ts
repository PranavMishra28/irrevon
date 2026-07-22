import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { validate, type Schema } from "../live-serve/mini-schema";

/**
 * Live-mode behavior against the test-local stub server (the frozen
 * handler shapes served over plain HTTP — see e2e/live-serve/stub-server.mjs
 * for the parity assumption with the real `irrevon serve`):
 *
 *  1. contract: every stub response validates against the same admitted
 *     schemas the engine is pinned to (validator first calibrated on the
 *     schemas/examples valid/invalid corpus)
 *  2. connected: real HTTP reads render, the LIVE chip shows, no MSW
 *  3. disconnected: killing the server flips the full-width banner while
 *     already-rendered data stays visible — never a fixture fallback
 *  4. unsupported version: schema_version 999 renders the blocking
 *     full-surface refusal with no route content behind it
 */

// One worker, in order: the suite builds an artifact and owns child processes.
test.describe.configure({ mode: "serial" });

const WEB_ROOT = join(import.meta.dirname, "../..");
const REPO_ROOT = join(WEB_ROOT, "..");
const LIVE_DIST = join(WEB_ROOT, "dist-live-stub");
const STUB = join(WEB_ROOT, "e2e/live-serve/stub-server.mjs");

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const AXE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

interface Stub {
  proc: ChildProcess;
  port: number;
  origin: string;
}

function startStub(env: Record<string, string> = {}): Promise<Stub> {
  return new Promise((resolve, reject) => {
    const proc = spawn("node", [STUB], {
      env: { ...process.env, IRREVON_STUB_DIST: LIVE_DIST, ...env },
      stdio: ["ignore", "pipe", "inherit"],
    });
    proc.once("error", reject);
    let buffer = "";
    proc.stdout.on("data", (chunk: Buffer) => {
      buffer += chunk.toString();
      const line = buffer.split("\n").find((l) => l.includes('"ready":true'));
      if (line) {
        const { port } = JSON.parse(line) as { port: number };
        resolve({ proc, port, origin: `http://127.0.0.1:${port}` });
      }
    });
  });
}

async function stopStub(stub: Stub): Promise<void> {
  // A signal-killed process has exitCode null but signalCode set.
  if (stub.proc.exitCode !== null || stub.proc.signalCode !== null) return;
  stub.proc.kill("SIGKILL");
  await new Promise((r) => stub.proc.once("exit", r));
}

test.beforeAll(() => {
  // A real production live artifact (MSW stripped, fixtures absent).
  execFileSync("pnpm", ["exec", "vite", "build", "--outDir", "dist-live-stub"], {
    cwd: WEB_ROOT,
    env: { ...process.env, VITE_IRREVON_DATA_MODE: "live" },
    stdio: "pipe",
  });
});

test("stub responses validate against the admitted contract schemas", async ({ request }) => {
  const loadSchema = (name: string): Schema =>
    JSON.parse(
      readFileSync(join(REPO_ROOT, "schemas", `${name}.schema.json`), "utf8"),
    ) as Schema;

  // Calibrate the mini-validator on the repo's example corpus first: every
  // valid example must pass and every invalid example must fail, or the
  // validator itself is not trustworthy enough to certify the stub.
  for (const name of ["effect-record", "reconciliation-finding", "capability-declaration"]) {
    const schema = loadSchema(name);
    const dir = join(REPO_ROOT, "schemas/examples", name);
    for (const file of readdirSync(dir)) {
      const example: unknown = JSON.parse(readFileSync(join(dir, file), "utf8"));
      const errors = validate(schema, example);
      if (file.startsWith("valid-")) {
        expect(errors, `${name}/${file} must validate`).toEqual([]);
      } else {
        expect(errors.length, `${name}/${file} must fail validation`).toBeGreaterThan(0);
      }
    }
  }

  const stub = await startStub();
  try {
    const get = async (path: string) => {
      const response = await request.get(`${stub.origin}${path}`);
      expect(response.status(), path).toBe(200);
      return (await response.json()) as Record<string, unknown>;
    };

    const effectRecordSchema = loadSchema("effect-record");
    const findingSchema = loadSchema("reconciliation-finding");
    const capabilitySchema = loadSchema("capability-declaration");

    // Q1 envelope: every item's record + finding validate against the pins.
    const effects = await get("/api/v1/effects");
    expect(effects.schema_version).toBe("1");
    expect(effects).toHaveProperty("has_more");
    expect(effects).toHaveProperty("next_cursor");
    expect(effects).toHaveProperty("as_of");
    const items = effects.data as {
      record: unknown;
      classification: string;
      finding: unknown;
    }[];
    expect(items.length).toBeGreaterThan(0);
    for (const item of items) {
      expect(validate(effectRecordSchema, item.record)).toEqual([]);
      if (item.finding !== null) expect(validate(findingSchema, item.finding)).toEqual([]);
      expect(typeof item.classification).toBe("string");
    }

    const findings = await get("/api/v1/findings");
    for (const finding of findings.data as unknown[]) {
      expect(validate(findingSchema, finding)).toEqual([]);
    }

    const adapters = await get("/api/v1/adapters");
    for (const declaration of adapters.data as unknown[]) {
      expect(validate(capabilitySchema, declaration)).toEqual([]);
    }

    // Prose-specified payloads (health, demo artifact, inspect) must be the
    // captured fixtures verbatim — the stub serves, never synthesizes.
    const health = await get("/api/v1/health");
    expect(health).toEqual(
      JSON.parse(readFileSync(join(WEB_ROOT, "fixtures/canonical/health.json"), "utf8")),
    );
    const artifact = await get("/api/v1/demo/artifact");
    expect(artifact).toEqual(
      JSON.parse(readFileSync(join(WEB_ROOT, "fixtures/canonical/demo-artifact.json"), "utf8")),
    );
    const inspect = await get(`/api/v1/effects/${FLAGSHIP}/inspect`);
    expect(inspect).toEqual(
      JSON.parse(
        readFileSync(join(WEB_ROOT, `fixtures/canonical/inspect/${FLAGSHIP}.json`), "utf8"),
      ),
    );

    // Unknown ids and unknown API routes 404 with the frozen error shape.
    const missing = await request.get(`${stub.origin}/api/v1/effects/${"f".repeat(64)}`);
    expect(missing.status()).toBe(404);
    expect(await missing.json()).toEqual({ error: "not_found" });
    const unknown = await request.get(`${stub.origin}/api/v1/nope`);
    expect(unknown.status()).toBe(404);
  } finally {
    await stopStub(stub);
  }
});

test("connected: live reads render real data with the LIVE chip, no MSW", async ({
  browser,
}) => {
  const stub = await startStub();
  const context = await browser.newContext({ baseURL: stub.origin });
  const page = await context.newPage();
  const workerRequests: string[] = [];
  page.on("request", (request) => {
    if (request.url().includes("mockServiceWorker")) workerRequests.push(request.url());
  });
  try {
    await page.goto(`${stub.origin}/effects`);
    await expect(page.getByRole("heading", { name: "Effects" })).toBeVisible();
    // Rows come from HTTP reads of the stub — the flagship effect renders.
    await expect(page.getByText("subscription.cancel").first()).toBeVisible({
      timeout: 15_000,
    });

    // The LIVE chip reaches connected off the health poll.
    const chip = page.getByTestId("live-chip");
    await expect(chip).toBeVisible();
    await expect(chip).toHaveAttribute("data-state", "connected", { timeout: 15_000 });

    // Live truth-in-labeling: no fixture banner, no disconnected banner.
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
    await stopStub(stub);
  }
});

test("disconnected: killing the engine flips the banner; data stays, no fixtures", async ({
  browser,
}) => {
  // The banner flips on the NEXT health poll: 15s interval + one retry —
  // the honest interval is not shortened for the test.
  test.setTimeout(90_000);
  const stub = await startStub();
  const context = await browser.newContext({ baseURL: stub.origin });
  const page = await context.newPage();
  try {
    await page.goto(`${stub.origin}/effects`);
    await expect(page.getByText("subscription.cancel").first()).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByTestId("live-chip")).toHaveAttribute("data-state", "connected", {
      timeout: 15_000,
    });

    // SIGKILL the server mid-session: the next health poll (15s interval,
    // one retry) must flip the full-width disconnected banner.
    await stopStub(stub);
    const banner = page.getByTestId("disconnected-banner");
    await expect(banner).toBeVisible({ timeout: 45_000 });
    await expect(banner).toContainText("Engine unreachable — data may be stale");

    // Already-rendered data stays visible (stale-marked by the banner) and
    // nothing falls back to fixture content — none exists in the bundle.
    await expect(page.getByText("subscription.cancel").first()).toBeVisible();
    await expect(page.getByText("Synthetic fixture — not live or measured")).toHaveCount(0);
    await expect(page.getByTestId("live-chip")).toHaveAttribute("data-state", "disconnected");

    // The disconnected state is itself accessible.
    const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations).toEqual([]);
  } finally {
    await context.close();
    await stopStub(stub);
  }
});

test("unsupported schema version: blocking full-surface refusal", async ({ browser }) => {
  const stub = await startStub({ IRREVON_STUB_SCHEMA_VERSION: "999" });
  const context = await browser.newContext({ baseURL: stub.origin });
  const page = await context.newPage();
  try {
    await page.goto(`${stub.origin}/`);
    const refusal = page.getByTestId("version-refusal");
    await expect(refusal).toBeVisible({ timeout: 15_000 });
    await expect(refusal).toContainText("supports schema_version 1");
    await expect(refusal).toContainText("999");

    // Blocking means blocking: no nav, no route content, no data behind it.
    await expect(page.getByRole("navigation")).toHaveCount(0);
    await expect(page.getByRole("link", { name: "Effects" })).toHaveCount(0);
    await expect(page.getByText("subscription.cancel")).toHaveCount(0);

    // Route content stays unreachable by direct URL too.
    await page.goto(`${stub.origin}/effects`);
    await expect(page.getByTestId("version-refusal")).toBeVisible({ timeout: 15_000 });
    await expect(page.getByRole("heading", { name: "Effects" })).toHaveCount(0);

    const results = await new AxeBuilder({ page }).withTags(AXE_TAGS).analyze();
    expect(results.violations).toEqual([]);
  } finally {
    await context.close();
    await stopStub(stub);
  }
});
