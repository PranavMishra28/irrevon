// Search/index policy shared by the Astro build, page layout, robots endpoint,
// and browser tests. Public search results are useful; internal result pages
// and error documents are not canonical destinations.
export const NOINDEX_PATHS = Object.freeze(["/404.html", "/docs/search/"]);
export const CRAWLER_RULES = Object.freeze([
  Object.freeze({ userAgent: "OAI-SearchBot", directive: "Allow", path: "/" }),
  Object.freeze({ userAgent: "PerplexityBot", directive: "Allow", path: "/" }),
  Object.freeze({ userAgent: "GPTBot", directive: "Disallow", path: "/" }),
  Object.freeze({ userAgent: "Google-Extended", directive: "Disallow", path: "/" }),
  Object.freeze({ userAgent: "CCBot", directive: "Disallow", path: "/" }),
  Object.freeze({ userAgent: "*", directive: "Allow", path: "/" }),
]);

export function normalizePathname(pathname) {
  if (
    typeof pathname !== "string" ||
    !pathname.startsWith("/") ||
    /[\u0000-\u001f\u007f\\?#]/u.test(pathname) ||
    /%(?:2e|2f|5c)/iu.test(pathname) ||
    pathname.includes("//")
  ) {
    return null;
  }
  if (pathname === "/404" || pathname === "/404/") return "/404.html";
  if (pathname.endsWith("/index.html")) return pathname.slice(0, -"index.html".length);
  if (pathname !== "/" && !pathname.includes(".") && !pathname.endsWith("/")) return `${pathname}/`;
  return pathname;
}

export function isIndexablePath(pathname) {
  const normalized = normalizePathname(pathname);
  return normalized !== null && !NOINDEX_PATHS.includes(normalized);
}

export function robotsDirective(pathname) {
  const normalized = normalizePathname(pathname);
  return normalized !== null && isIndexablePath(normalized)
    ? "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1"
    : normalized === "/docs/search/"
      ? "noindex,follow"
      : "noindex,nofollow";
}

export function renderRobots(sitemapUrl) {
  let sitemap;
  try {
    sitemap = new URL(sitemapUrl);
  } catch {
    throw new TypeError("robots sitemap must be the canonical HTTPS sitemap index URL");
  }
  const isLocalDevelopment =
    sitemap.protocol === "http:" && sitemap.hostname === "localhost" && !sitemap.username;
  if (
    sitemapUrl !== sitemap.href ||
    (sitemap.protocol !== "https:" && !isLocalDevelopment) ||
    sitemap.username ||
    sitemap.password ||
    sitemap.search ||
    sitemap.hash ||
    sitemap.pathname !== "/sitemap-index.xml"
  ) {
    throw new TypeError("robots sitemap must be the canonical HTTPS sitemap index URL");
  }
  return [
    ...CRAWLER_RULES.flatMap(({ userAgent, directive, path }) => [
      `User-agent: ${userAgent}`,
      `${directive}: ${path}`,
      "",
    ]),
    `Sitemap: ${sitemap.href}`,
    "",
  ].join("\n");
}
