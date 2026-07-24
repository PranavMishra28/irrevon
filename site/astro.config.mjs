// @ts-check
import { execFileSync, execSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig, passthroughImageService } from "astro/config";
import sitemap from "@astrojs/sitemap";
import { satteri } from "@astrojs/markdown-satteri";
import { repoLinksPlugin, scrollableFocusPlugin } from "./scripts/satteri-repo-links.mjs";
import { isIndexablePath } from "./search-policy.mjs";

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

const sharedPageSources = [
  "site/src/layouts/Base.astro",
  "site/src/lib/jsonld.ts",
];
const routeSources = new Map([
  ["/", "site/src/pages/index.astro"],
  ["/benchmark/", "site/src/pages/benchmark.astro"],
  ["/changelog/", "site/src/pages/changelog.astro"],
  ["/contributing/", "site/src/pages/contributing.astro"],
  ["/demo/", "site/src/pages/demo.astro"],
  ["/docs/", "site/src/pages/docs/index.astro"],
  ["/how-it-works/", "site/src/pages/how-it-works.astro"],
  ["/install/", "site/src/pages/install.astro"],
  ["/licensing/", "site/src/pages/licensing.astro"],
  ["/platform/", "site/src/pages/platform.astro"],
  ["/privacy/", "site/src/pages/privacy.astro"],
  ["/research/", "site/src/pages/research/index.astro"],
  ["/roadmap/", "site/src/pages/roadmap.astro"],
  ["/security/", "site/src/pages/security.astro"],
  ["/status/", "site/src/pages/status.astro"],
]);

function routeSource(pathname) {
  if (routeSources.has(pathname)) return routeSources.get(pathname);
  const guide = pathname.match(/^\/docs\/([^/]+)\/$/)?.[1];
  if (guide && guide !== "reference" && guide !== "search") return `site/src/content/guides/${guide}.md`;
  const reference = pathname.match(/^\/docs\/reference\/([^/]+)\/$/)?.[1];
  if (reference) {
    try {
      const manifest = JSON.parse(
        readFileSync(new URL("./docs-manifest.json", import.meta.url), "utf8"),
      );
      return manifest.render.find((entry) => entry.slug === reference)?.source;
    } catch {
      return undefined;
    }
  }
  const research = pathname.match(/^\/research\/([^/]+)\/$/)?.[1];
  if (research) return `site/src/content/research/${research}.md`;
  return undefined;
}

function lastSignificantUpdate(pageUrl) {
  const pathname = new URL(pageUrl).pathname;
  const sources = [routeSource(pathname), ...sharedPageSources].filter(Boolean);
  const dates = sources.flatMap((source) => {
    try {
      const value = execFileSync("git", ["log", "-1", "--format=%cs", "--", `:(top)${source}`], {
        encoding: "utf8",
      }).trim();
      return /^\d{4}-\d{2}-\d{2}$/.test(value) ? [value] : [];
    } catch {
      return [];
    }
  });
  return dates.sort().at(-1);
}

/** Origin for canonical/sitemap/OG URLs: deploy-provided, with the Vercel
 * production URL as fallback for platform builds; local builds use localhost. */
function productionOrigin(raw, source) {
  const parsed = new URL(raw);
  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.port ||
    parsed.pathname !== "/" ||
    parsed.search ||
    parsed.hash
  ) {
    throw new Error(`irrevon-site: ${source} must be a credential-free HTTPS origin with no path`);
  }
  return parsed.origin;
}

function resolveOrigin() {
  if (process.env.SITE_ORIGIN) return productionOrigin(process.env.SITE_ORIGIN, "SITE_ORIGIN");
  if (process.env.VERCEL_PROJECT_PRODUCTION_URL) {
    return productionOrigin(
      `https://${process.env.VERCEL_PROJECT_PRODUCTION_URL}`,
      "VERCEL_PROJECT_PRODUCTION_URL",
    );
  }
  return "http://localhost:4977";
}

// https://astro.build/config
export default defineConfig({
  output: "static",
  site: resolveOrigin(),
  base,
  trailingSlash: "always",
  image: { service: passthroughImageService() },
  // Sitemap entries are canonical, indexable HTML destinations only.
  integrations: [
    sitemap({
      filter: (page) => isIndexablePath(new URL(page).pathname),
      serialize: (item) => {
        const lastmod = lastSignificantUpdate(item.url);
        return lastmod ? { ...item, lastmod: new Date(`${lastmod}T00:00:00Z`) } : item;
      },
    }),
  ],
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
