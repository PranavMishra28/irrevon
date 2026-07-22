/**
 * Test-local live-serve stub — DEV/E2E ONLY, never shipped in any build.
 *
 * Serves the FROZEN handler shapes (web/src/mocks/handlers.ts +
 * web/src/shared/api/types.ts — the BE↔WEB integration contract at the
 * rename commit) over plain HTTP from the captured canonical fixtures, so
 * the live-mode Playwright specs run without the Python engine.
 *
 * PARITY ASSUMPTION (stop-and-flag on any deviation, never adapt): the
 * real `irrevon serve` (built separately by the serve workstream)
 * implements this exact surface — routes 1–9, the {schema_version, data,
 * has_more, next_cursor, as_of} list envelope, `{ "error": "not_found" }`
 * 404s, and payload schema_version "1". The stub-contract spec validates
 * every stub response against the same admitted schemas the engine is
 * pinned to; the real joint proof (demo → serve → Playwright) runs at
 * consolidation with the engine's own E2E fixture.
 *
 * Env:
 *   IRREVON_STUB_PORT             port to bind (0 = ephemeral; default 0)
 *   IRREVON_STUB_DIST             static root for the built live app (optional)
 *   IRREVON_STUB_SCHEMA_VERSION   override payload schema_version (default "1";
 *                                 set "999" for the refusal spec)
 *
 * Prints one ready line to stdout: {"ready":true,"port":<n>}
 */
import { createServer } from "node:http";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import { join, extname, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "../../fixtures/canonical");
const PORT = Number(process.env.IRREVON_STUB_PORT ?? "0");
const DIST = process.env.IRREVON_STUB_DIST ?? null;
const SCHEMA_VERSION = process.env.IRREVON_STUB_SCHEMA_VERSION ?? "1";

const loadJson = (name) => JSON.parse(readFileSync(join(FIXTURES, name), "utf8"));

const effectsFixture = loadJson("effects.json");
const findingsFixture = loadJson("findings.json");
const adaptersFixture = loadJson("adapters.json");
const healthFixture = loadJson("health.json");
const demoArtifactFixture = loadJson("demo-artifact.json");

const inspectPayloads = new Map(
  readdirSync(join(FIXTURES, "inspect"))
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const payload = loadJson(join("inspect", f));
      return [payload.record.effect_id, payload];
    }),
);

const records = effectsFixture.data;
const findings = findingsFixture.data;

/** Identical join to handlers.ts itemFor(): latest finding or UNRECONCILED. */
function itemFor(record) {
  const finding =
    findings.find(
      (f) => "effect_id" in f.subject && f.subject.effect_id === record.effect_id,
    ) ?? null;
  return {
    record,
    classification: finding ? finding.classification : "UNRECONCILED",
    finding,
  };
}

const PAGE_SIZE = 50;

function effectsEnvelope(url) {
  const lifecycle = url.searchParams.getAll("lifecycle");
  const classification = url.searchParams.getAll("classification");
  const effectType = url.searchParams.get("effect_type");
  const cursor = url.searchParams.get("cursor");

  let items = records.map(itemFor);
  if (lifecycle.length > 0) items = items.filter((i) => lifecycle.includes(i.record.lifecycle));
  if (classification.length > 0) {
    items = items.filter((i) => classification.includes(i.classification));
  }
  if (effectType !== null && effectType !== "") {
    items = items.filter((i) => i.record.effect_type === effectType);
  }

  const start = cursor === null ? 0 : Number.parseInt(cursor, 10) || 0;
  const page = items.slice(start, start + PAGE_SIZE);
  const hasMore = start + PAGE_SIZE < items.length;
  return {
    schema_version: "1",
    data: page,
    has_more: hasMore,
    next_cursor: hasMore ? String(start + PAGE_SIZE) : null,
    as_of: effectsFixture.as_of,
  };
}

function apiResponse(url) {
  const path = url.pathname;
  if (path === "/api/v1/effects") return { status: 200, body: effectsEnvelope(url) };
  const inspectMatch = /^\/api\/v1\/effects\/([^/]+)\/inspect$/.exec(path);
  if (inspectMatch) {
    const payload = inspectPayloads.get(inspectMatch[1]);
    return payload
      ? { status: 200, body: payload }
      : { status: 404, body: { error: "not_found" } };
  }
  const recordMatch = /^\/api\/v1\/effects\/([^/]+)$/.exec(path);
  if (recordMatch) {
    const record = records.find((r) => r.effect_id === recordMatch[1]);
    return record
      ? { status: 200, body: { schema_version: "1", ...itemFor(record) } }
      : { status: 404, body: { error: "not_found" } };
  }
  if (path === "/api/v1/findings") return { status: 200, body: findingsFixture };
  if (path === "/api/v1/adapters") return { status: 200, body: adaptersFixture };
  if (path === "/api/v1/health") return { status: 200, body: healthFixture };
  if (path === "/api/v1/demo/artifact") return { status: 200, body: demoArtifactFixture };
  return { status: 404, body: { error: "not_found" } };
}

const MIME = {
  ".html": "text/html",
  ".js": "text/javascript",
  ".css": "text/css",
  ".svg": "image/svg+xml",
  ".woff2": "font/woff2",
  ".json": "application/json",
  ".png": "image/png",
};

const server = createServer((req, res) => {
  const url = new URL(req.url ?? "/", "http://127.0.0.1");
  if (req.method !== "GET" && req.method !== "HEAD") {
    res.writeHead(405, { allow: "GET, HEAD", "content-type": "application/json" });
    res.end(JSON.stringify({ error: "method_not_allowed" }));
    return;
  }
  if (url.pathname.startsWith("/api/")) {
    const { status, body } = apiResponse(url);
    // The refusal stub: same shapes, foreign version — exercises the
    // client's schema_version gate, never a different envelope.
    const versioned =
      "schema_version" in body ? { ...body, schema_version: SCHEMA_VERSION } : body;
    res.writeHead(status, { "content-type": "application/json" });
    res.end(JSON.stringify(versioned));
    return;
  }
  if (DIST === null) {
    res.writeHead(404);
    res.end();
    return;
  }
  let filePath = join(DIST, url.pathname);
  if (!existsSync(filePath) || url.pathname === "/") filePath = join(DIST, "index.html");
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
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(JSON.stringify({ ready: true, port: server.address().port }));
});
