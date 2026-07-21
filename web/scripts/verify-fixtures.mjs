// Fixture drift gate: recompute SHA-256 over fixtures/canonical/** and compare
// with the committed manifest. Regeneration happens only via
// scripts/capture-fixtures.py against the real engine.
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const web = dirname(dirname(fileURLToPath(import.meta.url)));
const root = join(web, "fixtures");
const manifest = readFileSync(join(root, "manifest.sha256"), "utf8")
  .trim()
  .split("\n")
  .map((line) => {
    const [digest, name] = line.split(/\s+/);
    return { digest, name };
  });

function walk(dir) {
  return readdirSync(dir).flatMap((entry) => {
    const full = join(dir, entry);
    return statSync(full).isDirectory() ? walk(full) : [full];
  });
}

const actual = new Map(
  walk(join(root, "canonical")).map((file) => [
    relative(root, file),
    createHash("sha256").update(readFileSync(file)).digest("hex"),
  ]),
);

let failed = false;
for (const { digest, name } of manifest) {
  if (actual.get(name) !== digest) {
    console.error(`FIXTURE DRIFT: ${name}`);
    failed = true;
  }
  actual.delete(name);
}
for (const name of actual.keys()) {
  console.error(`UNMANIFESTED FIXTURE: ${name}`);
  failed = true;
}
if (failed) process.exit(1);
console.log(`fixtures in sync (${manifest.length} files)`);
