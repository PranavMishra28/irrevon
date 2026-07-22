// Renders the committed OG card set from og/template.svg (the N4 identity
// template — slots for product name, headline, footer). Rendering uses the
// already-pinned Playwright Chromium with the repository's own IBM Plex
// woff2 subsets embedded as data URLs — no new dependency, no build-time
// native step in CI.
//
// The PNGs are committed (public/og/) with og/manifest.json recording the
// template hash, the card configuration, and each PNG's sha256. `--check`
// verifies all three WITHOUT re-rendering (raster output is not
// byte-reproducible across platforms), so: a template or config change
// without regenerated cards fails CI, and a hand-swapped PNG fails CI.
// Regeneration (`pnpm og:build`) is the local act.
//
// Usage: node scripts/build-og.mjs [--check]

import { createHash } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const templateFile = join(siteRoot, "og", "template.svg");
const manifestFile = join(siteRoot, "og", "manifest.json");
const outDir = join(siteRoot, "public", "og");
const check = process.argv.includes("--check");

const PRODUCT_NAME = "Irrevon";
const FOOTER = "SEED 777 · RECORDED RUN · 1 DESTINATION EFFECT";

// One card per top section (+ the default). Two headline lines max, 64px.
const CARDS = {
  "og-default": ["Agents retry.", "Destinations don’t forgive."],
  "og-platform": ["Persist. Dispatch.", "Reconcile — with evidence."],
  "og-how-it-works": ["Identity from facts,", "never model output."],
  "og-demo": ["One crash, one retry.", "One destination effect."],
  "og-benchmark": ["Preregistered.", "No results yet — by design."],
  "og-docs": ["Documentation,", "drift-gated from the repo."],
  "og-research": ["Written before", "the results exist."],
  "og-install": ["Build from source today.", "Distribution: gated."],
};

const sha256 = (buf) => createHash("sha256").update(buf).digest("hex");
const esc = (s) => s.replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");

const template = readFileSync(templateFile, "utf8");
const templateSha256 = sha256(template);

function expectedManifest(pngHashes) {
  return `${JSON.stringify({ templateSha256, product: PRODUCT_NAME, footer: FOOTER, cards: CARDS, png: pngHashes }, null, 2)}\n`;
}

if (check) {
  let current;
  try {
    current = JSON.parse(readFileSync(manifestFile, "utf8"));
  } catch {
    console.error("build-og: og/manifest.json missing — run `pnpm og:build`");
    process.exit(1);
  }
  const pngHashes = {};
  let failed = false;
  for (const id of Object.keys(CARDS)) {
    const file = join(outDir, `${id}.png`);
    if (!existsSync(file)) {
      console.error(`build-og: missing committed card ${id}.png — run \`pnpm og:build\``);
      failed = true;
      continue;
    }
    pngHashes[id] = sha256(readFileSync(file));
  }
  if (failed || JSON.stringify(current, null, 2) + "\n" !== expectedManifest(pngHashes)) {
    console.error("build-og: DRIFT — template/config/PNGs disagree with og/manifest.json; run `pnpm og:build` and review the diff");
    process.exit(1);
  }
  console.log(`build-og: ${Object.keys(CARDS).length} OG cards match the template manifest`);
  process.exit(0);
}

const { chromium } = await import("@playwright/test");

const font = (file) =>
  `url(data:font/woff2;base64,${readFileSync(join(siteRoot, "src", "assets", "fonts", file)).toString("base64")}) format("woff2")`;
const fontCss = `
  @font-face { font-family: "IBM Plex Sans"; font-weight: 600; src: ${font("ibm-plex-sans-600.woff2")}; }
  @font-face { font-family: "IBM Plex Mono"; font-weight: 400; src: ${font("ibm-plex-mono-400.woff2")}; }
`;

mkdirSync(outDir, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1 });
const pngHashes = {};

for (const [id, [line1, line2]] of Object.entries(CARDS)) {
  const svg = template
    .replaceAll("{{PRODUCT_NAME}}", esc(PRODUCT_NAME))
    .replaceAll("{{HEADLINE_LINE_1}}", esc(line1))
    .replaceAll("{{HEADLINE_LINE_2}}", esc(line2))
    .replaceAll("{{FOOTER}}", esc(FOOTER));
  await page.setContent(
    `<!doctype html><html><head><style>${fontCss} html,body{margin:0;padding:0}</style></head><body>${svg}</body></html>`,
    { waitUntil: "networkidle" },
  );
  await page.evaluate(() => document.fonts.ready);
  const buf = await page.screenshot({ clip: { x: 0, y: 0, width: 1200, height: 630 } });
  writeFileSync(join(outDir, `${id}.png`), buf);
  pngHashes[id] = sha256(buf);
  console.log(`build-og: rendered ${id}.png (${buf.length} bytes)`);
}

await browser.close();
writeFileSync(manifestFile, expectedManifest(pngHashes));
console.log("build-og: wrote og/manifest.json");
