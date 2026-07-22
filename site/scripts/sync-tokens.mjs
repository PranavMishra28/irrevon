// Vendors the workbench reference tokens into site/src/styles/tokens/ and
// drift-checks the copy against the originals (no import or build coupling
// across package boundaries; one reviewable diff when tokens move).
//
// It also GENERATES a `@media (prefers-color-scheme: dark)` block from the
// `[data-theme="dark"]` rules so no-JS readers get a complete dark theme without
// hand-duplicating values (hand copies drift; generated copies cannot).
//
// Usage: node scripts/sync-tokens.mjs [--check]

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const webTokens = join(siteRoot, "..", "web", "src", "shared", "ui", "tokens");
const outFile = join(siteRoot, "src", "styles", "tokens", "reference.css");
const check = process.argv.includes("--check");

const source = readFileSync(join(webTokens, "reference.css"), "utf8");

const darkBlock = source.match(/\[data-theme="dark"\]\s*\{([\s\S]*?)\n\}/);
if (!darkBlock) throw new Error("sync-tokens: could not locate the dark theme block in web reference.css");
// Strip (possibly multi-line) comments first; keep declarations only.
const darkDecls = darkBlock[1]
  .replace(/\/\*[\s\S]*?\*\//g, "")
  .split("\n")
  .map((l) => l.trim())
  .filter((l) => l.startsWith("--") || l.startsWith("color-scheme"))
  .map((l) => `    ${l}`)
  .join("\n");

const header = `/* VENDORED COPY — do not edit by hand.
 * Source of truth: web/src/shared/ui/tokens/reference.css (Instrument Steel).
 * Synced by site/scripts/sync-tokens.mjs; \`--check\` fails CI on drift.
 * The trailing prefers-color-scheme block is GENERATED from the dark theme
 * rules above it so no-JS readers get the complete dark theme. */

`;

const generated = `
/* GENERATED from [data-theme="dark"] above — system dark preference without JS.
   An explicit data-theme attribute (set by the theme toggle) wins over this. */
@media (prefers-color-scheme: dark) {
  :root:not([data-theme]) {
${darkDecls}
  }
}
`;

const expected = header + source + generated;

if (check) {
  let current = "";
  try {
    current = readFileSync(outFile, "utf8");
  } catch {
    console.error("sync-tokens: vendored copy missing — run `pnpm sync:tokens`");
    process.exit(1);
  }
  if (current !== expected) {
    console.error("sync-tokens: DRIFT between web tokens and the vendored copy — run `pnpm sync:tokens` and review the diff");
    process.exit(1);
  }
  console.log("sync-tokens: vendored copy matches web/ source");
} else {
  mkdirSync(dirname(outFile), { recursive: true });
  writeFileSync(outFile, expected);
  console.log(`sync-tokens: wrote ${outFile}`);
}
