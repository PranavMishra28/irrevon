// @ts-check
import { execSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { defineConfig, passthroughImageService } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { satteri } from "@astrojs/markdown-satteri";
import { repoLinksPlugin, scrollableFocusPlugin } from "./scripts/satteri-repo-links.mjs";

/**
 * Repository URL is deployment-provided, never committed (DIST §1: nothing may
 * hard-code the working repo URL into a shipped artifact while the repo-identity
 * question is open). Resolution order:
 *   1. SITE_REPO_URL env (what a deploy build passes)
 *   2. Vercel git metadata (a git-connected Vercel build)
 *   3. the local git remote (developer builds in a clone)
 * A build with neither fails loudly — no page ships an unresolved source link.
 */
function resolveRepoUrl() {
  if (process.env.SITE_REPO_URL) return process.env.SITE_REPO_URL.replace(/\/$/, "");
  if (process.env.VERCEL_GIT_REPO_OWNER && process.env.VERCEL_GIT_REPO_SLUG) {
    return `https://github.com/${process.env.VERCEL_GIT_REPO_OWNER}/${process.env.VERCEL_GIT_REPO_SLUG}`;
  }
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

const repoUrl = resolveRepoUrl();
function resolveBuildCommit() {
  const candidate = process.env.VERCEL_GIT_COMMIT_SHA;
  if (candidate && /^[0-9a-f]{40}$/.test(candidate)) return candidate;
  try {
    const local = execSync("git rev-parse HEAD", { encoding: "utf8" }).trim();
    if (/^[0-9a-f]{40}$/.test(local)) return local;
  } catch {
    // handled below
  }
  throw new Error("irrevon-site: exact 40-character build commit is required");
}
const buildCommit = resolveBuildCommit();
// The site serves at the origin root (Vercel deploy, ADR-0027); no base path.
const base = "/";

/** Origin for canonical/sitemap/OG URLs: deploy-provided, with the Vercel
 * production URL as fallback for platform builds; local builds use localhost. */
function resolveOrigin() {
  if (process.env.SITE_ORIGIN) return process.env.SITE_ORIGIN.replace(/\/$/, "");
  if (process.env.VERCEL_PROJECT_PRODUCTION_URL) {
    return `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`;
  }
  return "http://localhost:4977";
}

// https://astro.build/config
export default defineConfig({
  output: "static",
  site: resolveOrigin(),
  base,
  trailingSlash: "ignore",
  image: { service: passthroughImageService() },
  // sitemap-index.xml + sitemap-0.xml; URLs derive from `site`, so the
  // deploy-provided origin/base flow through with zero new code. /404 is
  // excluded (an error page is not a destination).
  integrations: [sitemap({ filter: (page) => !page.includes("/404") })],
  markdown: {
    // Plain code blocks, no syntax highlighting: the hand-authored pages set
    // that register (structural ink, mono on sunken panel), theme-pair
    // switching would need four-state CSS wiring, and un-tinted code cannot
    // fail the contrast gate. Recorded as a deliberate deviation.
    syntaxHighlight: false,
    // Rendered repo docs keep their repo-relative links in the committed
    // copies; this build-time plugin resolves them to rendered sibling pages
    // or the repository on GitHub (scripts/satteri-repo-links.mjs).
    processor: satteri({
      mdastPlugins: [
        repoLinksPlugin({
          manifestPath: fileURLToPath(new URL("./docs-manifest.json", import.meta.url)),
          repoUrl,
          buildCommit,
          base,
        }),
      ],
      hastPlugins: [scrollableFocusPlugin()],
    }),
  },
  vite: {
    define: {
      __REPO_URL__: JSON.stringify(repoUrl),
      __BUILD_COMMIT__: JSON.stringify(buildCommit),
    },
  },
});
