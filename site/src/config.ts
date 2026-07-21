// One configurable project name (the name screen is pending — review-queue item 4;
// the site must be renameable by config, RD5 §3.9) and the deployment-provided
// repository URL (resolved in astro.config.mjs, never committed).

export const SITE_NAME = "Detent";
export const BENCH_NAME = `${SITE_NAME}Bench`;

declare const __REPO_URL__: string;
export const REPO_URL = __REPO_URL__;

/** Link to a repository file on the default branch without pinning a branch name. */
export const repoDoc = (path: string): string => `${REPO_URL}/blob/HEAD/${path}`;
