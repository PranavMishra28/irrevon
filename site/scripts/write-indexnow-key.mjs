// Build-only IndexNow ownership file. The value is deployment-provided,
// low-sensitivity proof material and never committed or logged.
import { existsSync, rmSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const output = join(process.cwd(), "dist", "indexnow-key.txt");
const key = process.env.INDEXNOW_KEY?.trim();
if (!key) {
  if (existsSync(output)) rmSync(output);
  process.exit(0);
}
if (!/^[A-Za-z0-9-]{8,128}$/.test(key)) {
  throw new Error("INDEXNOW_KEY must be 8–128 ASCII letters, digits, or hyphens");
}
writeFileSync(output, `${key}\n`, { encoding: "utf8", mode: 0o644 });
