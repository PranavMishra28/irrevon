// Vendors the self-hosted IBM Plex woff2 subsets (and their OFL license) from
// web/public/fonts into site/public/fonts — same fonts:sync pattern web/ uses.
// `--check` fails CI when the copies drift from the web/ originals.
//
// Usage: node scripts/sync-fonts.mjs [--check]

import { readFileSync, writeFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const siteRoot = join(here, "..");
const src = join(siteRoot, "..", "web", "public", "fonts");
// Fonts live under src/assets so Vite fingerprints them into /_astro/ and
// rewrites the CSS urls — base-safe by construction, and they ride the
// immutable cache rule for hashed assets (repository-root vercel.json).
const dst = join(siteRoot, "src", "assets", "fonts");
const check = process.argv.includes("--check");

const files = [
  "ibm-plex-sans-400.woff2",
  "ibm-plex-sans-500.woff2",
  "ibm-plex-sans-600.woff2",
  "ibm-plex-mono-400.woff2",
  "ibm-plex-mono-500.woff2",
  "OFL.txt",
];

let drift = false;
mkdirSync(dst, { recursive: true });
for (const f of files) {
  const want = readFileSync(join(src, f));
  if (check) {
    let have = null;
    try {
      have = readFileSync(join(dst, f));
    } catch {
      /* missing counts as drift */
    }
    if (!have || !want.equals(have)) {
      console.error(`sync-fonts: DRIFT ${f} — run \`pnpm sync:fonts\``);
      drift = true;
    }
  } else {
    writeFileSync(join(dst, f), want);
  }
}
if (check && drift) process.exit(1);
console.log(check ? "sync-fonts: vendored fonts match web/ source" : `sync-fonts: wrote ${files.length} files`);
