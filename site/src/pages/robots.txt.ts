// Search/index crawlers remain welcome. Named training/data crawlers are a
// separate policy choice; robots is advisory and does not alter Apache-2.0.
import type { APIContext } from "astro";
import { renderRobots } from "../../search-policy.mjs";

export function GET(context: APIContext) {
  const sitemap = new URL(`${import.meta.env.BASE_URL.replace(/\/$/, "")}/sitemap-index.xml`, context.site);
  const isVercelPreview = Boolean(process.env.VERCEL_ENV && process.env.VERCEL_ENV !== "production");
  const productionPolicy = renderRobots(sitemap.href);
  const body = isVercelPreview
    ? ["User-agent: *", "Disallow: /", ""].join("\n")
    : productionPolicy;
  return new Response(body, {
    headers: {
      "Content-Type": "text/plain; charset=utf-8",
      "Cache-Control": "public, max-age=300, must-revalidate",
    },
  });
}
