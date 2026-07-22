// Build provenance (owner completion directive, 2026-07-22): every deployed
// page discloses which repository commit it was built from and when. Values
// are resolved ONCE at build time: on Vercel from the deployment's git
// metadata (VERCEL_GIT_COMMIT_SHA — provided by the platform at build), else
// from the local git checkout, else honestly "unknown". A static build cannot
// know whether it still matches the current default branch — that caveat is
// part of the rendered text, never silently implied.

import { execSync } from "node:child_process";

function resolveCommit(): string | null {
  const fromVercel = process.env.VERCEL_GIT_COMMIT_SHA;
  if (fromVercel && /^[0-9a-f]{7,40}$/.test(fromVercel)) return fromVercel;
  try {
    const local = execSync("git rev-parse HEAD", {
      encoding: "utf8",
      timeout: 5000,
      stdio: ["ignore", "pipe", "ignore"],
    }).trim();
    return /^[0-9a-f]{40}$/.test(local) ? local : null;
  } catch {
    return null;
  }
}

export const BUILD_COMMIT: string | null = resolveCommit();
export const BUILD_COMMIT_SHORT: string | null = BUILD_COMMIT ? BUILD_COMMIT.slice(0, 12) : null;
export const BUILT_AT: string = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
