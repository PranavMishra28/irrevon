// @ts-check
import { execSync } from "node:child_process";
import { defineConfig, passthroughImageService } from "astro/config";

/**
 * Repository URL is deployment-provided, never committed (DIST §1: nothing may
 * hard-code the working repo URL into a shipped artifact while the repo-identity
 * question is open). Resolution order:
 *   1. SITE_REPO_URL env (what the deploy workflow passes)
 *   2. the local git remote (developer builds in a clone)
 * A build with neither fails loudly — no page ships an unresolved source link.
 */
function resolveRepoUrl() {
  if (process.env.SITE_REPO_URL) return process.env.SITE_REPO_URL.replace(/\/$/, "");
  try {
    const raw = execSync("git remote get-url origin", { encoding: "utf8" }).trim();
    const m = raw.match(/^git@([^:]+):(.+?)(\.git)?$/);
    const url = m ? `https://${m[1]}/${m[2]}` : raw.replace(/\.git$/, "");
    return url.replace(/\/$/, "");
  } catch {
    throw new Error(
      "irrevon-site: repository URL unresolved. Set SITE_REPO_URL or build inside a clone with an origin remote.",
    );
  }
}

// https://astro.build/config
export default defineConfig({
  output: "static",
  // Project-site base path for GitHub Pages: the deploy workflow passes
  // --site/--base from actions/configure-pages outputs; local builds serve at /.
  site: process.env.SITE_ORIGIN ?? "http://localhost:4977",
  base: process.env.SITE_BASE ?? "/",
  trailingSlash: "ignore",
  image: { service: passthroughImageService() },
  vite: {
    define: {
      __REPO_URL__: JSON.stringify(resolveRepoUrl()),
    },
  },
});
