// One configurable project name (Irrevon per ADR-0023; kept configurable so a
// future rename is one edit) and the deployment-provided repository URL (resolved in
// astro.config.mjs, never committed).

export const SITE_NAME = "Irrevon";
export const BENCH_NAME = `${SITE_NAME}Bench`;

declare const __REPO_URL__: string;
declare const __BUILD_COMMIT__: string;
export const REPO_URL = __REPO_URL__;
export const BUILD_SOURCE_COMMIT = __BUILD_COMMIT__;

/** Secondary provenance link pinned to the exact site build commit. */
export const repoDoc = (path: string): string =>
  `${REPO_URL}/blob/${BUILD_SOURCE_COMMIT}/${path}`;
