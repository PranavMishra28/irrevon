// Copies the IBM Plex Latin1 subsets (weights 400/500/600, upright only) from the
// npm packages into public/fonts, plus the OFL license. Committed output; --check
// verifies the committed files match the package bytes (drift gate).
import { createHash } from "node:crypto";
import { copyFileSync, existsSync, mkdirSync, readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = dirname(dirname(fileURLToPath(import.meta.url)));
const outDir = join(root, "public", "fonts");
const check = process.argv.includes("--check");

const files = [
  ["@ibm/plex-sans", "IBMPlexSans-Regular-Latin1.woff2", "ibm-plex-sans-400.woff2"],
  ["@ibm/plex-sans", "IBMPlexSans-Medium-Latin1.woff2", "ibm-plex-sans-500.woff2"],
  ["@ibm/plex-sans", "IBMPlexSans-SemiBold-Latin1.woff2", "ibm-plex-sans-600.woff2"],
  ["@ibm/plex-mono", "IBMPlexMono-Regular-Latin1.woff2", "ibm-plex-mono-400.woff2"],
  ["@ibm/plex-mono", "IBMPlexMono-Medium-Latin1.woff2", "ibm-plex-mono-500.woff2"],
  ["@ibm/plex-mono", "IBMPlexMono-SemiBold-Latin1.woff2", "ibm-plex-mono-600.woff2"],
];

const sha = (p) => createHash("sha256").update(readFileSync(p)).digest("hex");

let failed = false;
mkdirSync(outDir, { recursive: true });

for (const [pkg, srcName, outName] of files) {
  const src = join(root, "node_modules", pkg, "fonts", "split", "woff2", srcName);
  const out = join(outDir, outName);
  if (check) {
    if (!existsSync(out) || sha(src) !== sha(out)) {
      console.error(`DRIFT: ${outName} does not match ${pkg}/${srcName}`);
      failed = true;
    }
  } else {
    copyFileSync(src, out);
    console.log(`wrote ${outName}`);
  }
}

const licenseSrc = join(root, "node_modules", "@ibm/plex-sans", "LICENSE.txt");
const licenseOut = join(outDir, "OFL.txt");
if (check) {
  if (!existsSync(licenseOut) || sha(licenseSrc) !== sha(licenseOut)) {
    console.error("DRIFT: OFL.txt does not match the package license");
    failed = true;
  }
} else {
  copyFileSync(licenseSrc, licenseOut);
  console.log("wrote OFL.txt");
}

if (check && failed) process.exit(1);
if (check) console.log("fonts in sync");
