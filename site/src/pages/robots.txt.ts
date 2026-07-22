// robots.txt, generated so the sitemap URL derives from the deploy-provided
// origin/base. Honest caveat (recorded in site/README.md): on a project
// Pages site this file is not served at the origin root and is therefore
// not authoritative per RFC 9309; it becomes real the day a custom domain
// exists. Emitting it now costs nothing and is correct later.
import type { APIContext } from "astro";

export function GET(context: APIContext) {
  const sitemap = new URL(`${import.meta.env.BASE_URL.replace(/\/$/, "")}/sitemap-index.xml`, context.site);
  const body = ["User-agent: *", "Allow: /", "", `Sitemap: ${sitemap}`, ""].join("\n");
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8" } });
}
