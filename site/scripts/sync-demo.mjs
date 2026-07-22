// Syncs the recorded demo artifact (and the flagship inspect record it
// cites) from the workbench fixtures into site/src/data/, drift-gated — the
// same pattern as tokens/fonts/claims/docs. The /demo page renders every
// number, id, and status from these files at build time, so a fabricated
// value is structurally impossible; if the workbench artifact changes
// without a re-sync, the site build fails.
//
// Usage: node scripts/sync-demo.mjs [--check]

import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const fixtures = join(siteRoot, "..", "web", "fixtures", "canonical");
const outDir = join(siteRoot, "src", "data", "demo");
const check = process.argv.includes("--check");

const FLAGSHIP = "0bb7e8d64711e0cc5ec277fb9bb64d3d321fdd53dd92b8ebb1752fde822785f5";
const FILES = [
  { src: join(fixtures, "demo-artifact.json"), out: "demo-artifact.json" },
  { src: join(fixtures, "provenance.json"), out: "provenance.json" },
  { src: join(fixtures, "inspect", `${FLAGSHIP}.json`), out: "flagship-inspect.json" },
];

mkdirSync(outDir, { recursive: true });
let failed = false;

for (const { src, out } of FILES) {
  const expected = readFileSync(src, "utf8");
  const outFile = join(outDir, out);
  const current = existsSync(outFile) ? readFileSync(outFile, "utf8") : null;
  if (check) {
    if (current !== expected) {
      console.error(`sync-demo: DRIFT in ${out} vs ${src} — run \`pnpm sync:demo\``);
      failed = true;
    }
  } else if (current !== expected) {
    writeFileSync(outFile, expected);
    console.log(`sync-demo: wrote ${out}`);
  }
}

if (check && failed) process.exit(1);
console.log(`sync-demo: ${FILES.length} recorded artifacts ${check ? "match" : "in sync with"} web/fixtures/canonical`);
