// Research RSS feed (@astrojs/rss, first-party). Absolute URLs derive from
// the deployment-provided site origin + base path — nothing hard-coded.
// The changelog feed is deliberately ABSENT until the first release entry
// exists: an empty feed advertises a subscription to nothing.
import rss from "@astrojs/rss";
import { getCollection } from "astro:content";
import type { APIContext } from "astro";
import { SITE_NAME } from "../../config";
import { href } from "../../lib/url";

export async function GET(context: APIContext) {
  const posts = (await getCollection("research")).sort((a, b) => b.data.date.localeCompare(a.data.date));
  return rss({
    title: `${SITE_NAME} — Research`,
    description:
      "Research notes from the Irrevon project: benchmark preregistration, prior art, and research integrity.",
    site: context.site!,
    items: posts.map((p) => ({
      title: p.data.title,
      description: p.data.summary,
      pubDate: new Date(`${p.data.date}T00:00:00Z`),
      link: href(`/research/${p.id}/`),
    })),
  });
}
