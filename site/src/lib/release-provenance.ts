import { readFileSync } from "node:fs";
import { resolve } from "node:path";

function exactVersion(file: string, pattern: RegExp, label: string): string {
  const source = readFileSync(file, "utf8");
  const match = source.match(pattern);
  if (!match?.[1]) throw new Error(`irrevon-site: cannot resolve ${label}`);
  return match[1];
}

export const RELEASE_VERSION = exactVersion(
  resolve(process.cwd(), "../src/irrevon/__init__.py"),
  /^__version__\s*=\s*"([^"]+)"$/m,
  "release version",
);

export const SCHEMA_VERSION = exactVersion(
  resolve(process.cwd(), "../src/irrevon/__init__.py"),
  /^SCHEMA_VERSION\s*=\s*"([^"]+)"$/m,
  "schema version",
);

export const BENCHMARK_HARNESS_VERSION = exactVersion(
  resolve(process.cwd(), "../src/irrevon/bench/__init__.py"),
  /^HARNESS_VERSION\s*=\s*"([^"]+)"$/m,
  "benchmark harness version",
);

const rawEnvironment = process.env.VERCEL_ENV ?? process.env.SITE_ENVIRONMENT ?? "development";
if (!["production", "preview", "development"].includes(rawEnvironment)) {
  throw new Error("irrevon-site: environment must be production, preview, or development");
}
export const BUILD_ENVIRONMENT = rawEnvironment;
