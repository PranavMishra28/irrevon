import { readFileSync } from "node:fs";
import { resolve } from "node:path";

export type SoftwareReleaseState = "candidate" | "published";

export interface SoftwareRelease {
  state: SoftwareReleaseState;
  package: "irrevon";
  version: string;
  tag: string;
  channel: "alpha";
  pypi_url: string;
  github_release_url: string;
  published_at: string | null;
  commit_sha: string | null;
}

function exactVersion(file: string, pattern: RegExp, label: string): string {
  const source = readFileSync(file, "utf8");
  const match = source.match(pattern);
  if (!match?.[1]) throw new Error(`irrevon-site: cannot resolve ${label}`);
  return match[1];
}

const packageVersion = exactVersion(
  resolve(process.cwd(), "../src/irrevon/__init__.py"),
  /^__version__\s*=\s*"([^"]+)"$/m,
  "release version",
);

export function parseSoftwareRelease(value: unknown): SoftwareRelease {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("irrevon-site: software_release must be an object");
  }
  const release = value as Record<string, unknown>;
  const state = release.state;
  if (state !== "candidate" && state !== "published") {
    throw new Error("irrevon-site: software_release.state must be candidate or published");
  }
  if (release.package !== "irrevon") {
    throw new Error("irrevon-site: software_release.package must be irrevon");
  }
  if (
    typeof release.version !== "string" ||
    !/^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)$/.test(release.version)
  ) {
    throw new Error("irrevon-site: software_release.version must be semantic");
  }
  if (release.version !== packageVersion || release.tag !== `v${release.version}`) {
    throw new Error("irrevon-site: software release version, package, and tag must agree");
  }
  if (release.channel !== "alpha") {
    throw new Error("irrevon-site: v0.1.0 must retain the alpha channel");
  }
  if (release.pypi_url !== `https://pypi.org/project/irrevon/${release.version}/`) {
    throw new Error("irrevon-site: software_release.pypi_url is not canonical");
  }
  if (
    release.github_release_url !==
    `https://github.com/PranavMishra28/irrevon/releases/tag/v${release.version}`
  ) {
    throw new Error("irrevon-site: software_release.github_release_url is not canonical");
  }

  const publishedAt = release.published_at;
  const commitSha = release.commit_sha;
  if (state === "candidate") {
    if (publishedAt !== null || commitSha !== null) {
      throw new Error("irrevon-site: candidate release cannot carry publication evidence");
    }
  } else if (
    typeof publishedAt !== "string" ||
    !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$/.test(publishedAt) ||
    typeof commitSha !== "string" ||
    !/^[0-9a-f]{40}$/.test(commitSha)
  ) {
    throw new Error("irrevon-site: published release requires timestamp and commit evidence");
  }

  return release as unknown as SoftwareRelease;
}

const statusDocument = JSON.parse(
  readFileSync(resolve(process.cwd(), "../docs/project-status.json"), "utf8"),
) as Record<string, unknown>;
export const SOFTWARE_RELEASE = parseSoftwareRelease(statusDocument.software_release);
export const RELEASE_STATE = SOFTWARE_RELEASE.state;
export const RELEASE_VERSION = SOFTWARE_RELEASE.version;
export const RELEASE_TAG = SOFTWARE_RELEASE.tag;
export const PYPI_PROJECT_URL = SOFTWARE_RELEASE.pypi_url;
export const GITHUB_RELEASE_URL = SOFTWARE_RELEASE.github_release_url;
export const RELEASED_AT = SOFTWARE_RELEASE.published_at;
export const RELEASE_COMMIT = SOFTWARE_RELEASE.commit_sha;

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
