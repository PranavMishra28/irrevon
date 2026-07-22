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

const repoUrl = resolveRepoUrl();
const base = process.env.SITE_BASE ?? "/";

// https://astro.build/config
export default defineConfig({
  output: "static",
  // Project-site base path for GitHub Pages: the deploy workflow passes
  // --site/--base from actions/configure-pages outputs; local builds serve at /.
  site: process.env.SITE_ORIGIN ?? "http://localhost:4977",
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
          base,
        }),
      ],
      hastPlugins: [scrollableFocusPlugin()],
    }),
  },
  vite: {
    define: {
      __REPO_URL__: JSON.stringify(repoUrl),
    },
  },
});
