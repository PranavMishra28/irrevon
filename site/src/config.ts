// One configurable project name (Irrevon per ADR-0023; kept configurable per
// RD5 §3.9) and the deployment-provided repository URL (resolved in
// astro.config.mjs, never committed).

export const SITE_NAME = "Irrevon";
export const BENCH_NAME = `${SITE_NAME}Bench`;

declare const __REPO_URL__: string;
export const REPO_URL = __REPO_URL__;

/** Link to a repository file on the default branch without pinning a branch name. */
export const repoDoc = (path: string): string => `${REPO_URL}/blob/HEAD/${path}`;
