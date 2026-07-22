// Build-time link rewriting for markdown content, as a Sätteri mdast plugin
// (Astro 7's native markdown pipeline).
//
// - Rendered repository docs (repo-docs collection, identified by their
//   sourcePath frontmatter) keep their original repo-relative links in the
//   committed copies — sync-docs.mjs never embeds a repository URL. Here each
//   link resolves against the doc's sourcePath and points at either the
//   rendered sibling page (when the target is in docs-manifest.json) or the
//   repository file on GitHub.
// - Authored content (guides, research) gets base-path prefixing for
//   site-absolute links only.
//
// Local and dependency-free beyond the pipeline Astro already ships, per the
// hardening register.

import { readFileSync } from "node:fs";
import path from "node:path";

export function repoLinksPlugin({ manifestPath, repoUrl, base }) {
  const manifest = JSON.parse(readFileSync(manifestPath, "utf8"));
  const slugBySource = new Map(manifest.render.map((e) => [e.source, e.slug]));
  const prefix = base.replace(/\/$/, "");

  const rewrite = (url, sourceDir) => {
    // Site-absolute links (authored content) get the deploy base path.
    if (url.startsWith("/")) return `${prefix}${url}`;
    if (/^[a-z][a-z0-9+.-]*:/i.test(url) || url.startsWith("#")) return url;
    if (sourceDir === null) return url;
    const [target, fragment] = url.split("#");
    if (!target) return url;
    const repoPath = path.posix.normalize(path.posix.join(sourceDir, target)).replace(/\/$/, "");
    const frag = fragment ? `#${fragment}` : "";
    const slug = slugBySource.get(repoPath);
    if (slug) return `${prefix}/docs/reference/${slug}/${frag}`;
    return `${repoUrl}/blob/HEAD/${repoPath}${frag}`;
  };

  const visit = (node, ctx) => {
    if (typeof node.url !== "string") return;
    const sourcePath = ctx.data?.astro?.frontmatter?.sourcePath;
    const sourceDir = typeof sourcePath === "string" ? path.posix.dirname(sourcePath) : null;
    const next = rewrite(node.url, sourceDir);
    if (next !== node.url) ctx.setProperty(node, "url", next);
  };

  return {
    name: "repo-links",
    link: visit,
    definition: visit,
  };
}
