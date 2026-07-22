// The page inventory is derived from the built output (dist/), so every new
// page is automatically under the axe/budget/link gates — a page cannot ship
// untested by being forgotten here.
import { readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const dist = fileURLToPath(new URL("../dist", import.meta.url));

function walk(dir: string, prefix: string): string[] {
  const routes: string[] = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.isDirectory()) {
      if (entry.name === "pagefind" || entry.name === "_astro") continue;
      routes.push(...walk(join(dir, entry.name), `${prefix}${entry.name}/`));
    } else if (entry.name === "index.html") {
      routes.push(prefix);
    }
  }
  return routes;
}

export const PAGES = walk(dist, "/").sort() as readonly string[];
// The 404 page is served for unmatched routes by the static host (Vercel).
export const ERROR_PAGES = ["/404.html"] as const;
export const ALL_PAGES = [...PAGES, ...ERROR_PAGES];

export const DOCS_PAGES = PAGES.filter((p) => p.startsWith("/docs/") || p === "/docs/");
export const NON_DOCS_PAGES = ALL_PAGES.filter((p) => !DOCS_PAGES.includes(p));
