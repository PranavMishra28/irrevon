// Built-output discoverability contract.
//
// These are project-specific regression gates, not promises that a crawler
// will index, rank, cite, or enrich a page. In particular, the modest content
// floor and duplicate-page heuristic exist to catch accidental empty/template
// output; they are not SEO word-count or keyword-density targets.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { expect, test } from "@playwright/test";
import { ALL_PAGES, PAGES } from "./pages";
import { isIndexablePath, normalizePathname, robotsDirective } from "../search-policy.mjs";

type Intent = {
  primary_intent: string;
  supporting_concepts: string[];
};

type IntentPolicy = {
  pages: Record<string, Intent>;
  patterns: Array<{ prefix: string } & Intent>;
  noindex: Record<string, string>;
};

type Snapshot = {
  path: string;
  title: string;
  descriptions: string[];
  robots: string[];
  keywords: string[];
  canonicals: string[];
  h1s: string[];
  mainText: string;
  pageText: string;
  runtimeOrigin: string;
  social: Record<string, string[]>;
  jsonLd: string[];
  internalLinks: Array<{ href: string; rel: string }>;
  videos: Array<{
    poster: string;
    sources: string[];
    tracks: Array<{ kind: string; src: string; srclang: string }>;
  }>;
  publicVideoLinks: string[];
  transcriptText: string;
  analytics: Array<{
    event: string | null;
    copyEvent: string | null;
    placement: string | null;
    attributes: string[];
  }>;
};

const intentPolicy = JSON.parse(
  readFileSync(fileURLToPath(new URL("../search-intents.json", import.meta.url)), "utf8"),
) as IntentPolicy;

const allowedEvents = new Set([
  "repository_click",
  "clone_command_copy",
  "install_command_copy",
  "demo_start",
  "demo_complete",
  "video_start",
  "video_complete",
  "workbench_exploration",
  "documentation_entry",
  "benchmark_methodology_visit",
  "adapter_guide_visit",
  "contribution_click",
  "security_report_click",
  "launch_cta",
]);
const allowedPlacements = new Set([
  "header",
  "hero",
  "proof",
  "body",
  "footer",
  "install",
  "docs",
  "benchmark",
  "demo",
]);

const normalize = (value: string) => value.replace(/\s+/g, " ").trim();
const comparable = (value: string) => normalize(value).toLocaleLowerCase("en-US");
const words = (value: string) => comparable(value).match(/[a-z0-9]+/g) ?? [];
const significantWords = (value: string) =>
  new Set(
    words(value).filter(
      (word) =>
        word.length >= 5 &&
        !new Set([
          "about",
          "canonical",
          "complete",
          "current",
          "irrevon",
          "public",
          "read",
          "specific",
          "through",
          "understand",
        ]).has(word),
    ),
  );

function intentFor(path: string): Intent | undefined {
  return intentPolicy.pages[path] ?? intentPolicy.patterns.find(({ prefix }) => path.startsWith(prefix));
}

function shingles(value: string, width = 5): Set<string> {
  const tokens = words(value).slice(0, 1_200);
  const result = new Set<string>();
  for (let index = 0; index <= tokens.length - width; index += 1) {
    result.add(tokens.slice(index, index + width).join(" "));
  }
  return result;
}

function jaccard(left: Set<string>, right: Set<string>): number {
  if (left.size === 0 || right.size === 0) return 0;
  let intersection = 0;
  for (const value of left) if (right.has(value)) intersection += 1;
  return intersection / (left.size + right.size - intersection);
}

function collectJsonKeys(value: unknown, keys = new Set<string>()): Set<string> {
  if (Array.isArray(value)) {
    for (const item of value) collectJsonKeys(item, keys);
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      keys.add(key);
      collectJsonKeys(child, keys);
    }
  }
  return keys;
}

function collectJsonTypes(value: unknown, types = new Set<string>()): Set<string> {
  if (Array.isArray(value)) {
    for (const item of value) collectJsonTypes(item, types);
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      if (key === "@type" && typeof child === "string") types.add(child);
      collectJsonTypes(child, types);
    }
  }
  return types;
}

function jsonObjectsOfType(value: unknown, type: string, found: Array<Record<string, unknown>> = []) {
  if (Array.isArray(value)) {
    for (const item of value) jsonObjectsOfType(item, type, found);
  } else if (value && typeof value === "object") {
    const record = value as Record<string, unknown>;
    if (record["@type"] === type) found.push(record);
    for (const child of Object.values(record)) jsonObjectsOfType(child, type, found);
  }
  return found;
}

function xmlValue(fragment: string, tag: string): string | undefined {
  const match = fragment.match(new RegExp(`<${tag}>([^<]+)</${tag}>`));
  return match?.[1]
    .replaceAll("&amp;", "&")
    .replaceAll("&lt;", "<")
    .replaceAll("&gt;", ">")
    .replaceAll("&quot;", '"')
    .replaceAll("&apos;", "'");
}

test("generated public pages have coherent, unique, honest discovery metadata and substantive content", async ({
  page,
}) => {
  test.setTimeout(180_000);
  const snapshots: Snapshot[] = [];
  const checkedSocialImages = new Set<string>();

  for (const path of ALL_PAGES) {
    await page.goto(path, { waitUntil: "domcontentloaded" });
    const snapshot = await page.evaluate((currentPath) => {
      const contents = (selector: string) =>
        Array.from(document.querySelectorAll<HTMLMetaElement>(selector), (element) => element.content);
      const hrefs = (selector: string) =>
        Array.from(document.querySelectorAll<HTMLLinkElement>(selector), (element) => element.href);
      return {
        path: currentPath,
        title: document.title,
        descriptions: contents("meta[name='description']"),
        robots: contents("meta[name='robots']"),
        keywords: contents("meta[name='keywords']"),
        canonicals: hrefs("link[rel='canonical']"),
        h1s: Array.from(document.querySelectorAll("main h1"), (element) => element.textContent ?? ""),
        mainText: (document.querySelector("main") as HTMLElement | null)?.innerText ?? "",
        pageText: document.body.innerText,
        runtimeOrigin: location.origin,
        social: {
          ogType: contents("meta[property='og:type']"),
          ogTitle: contents("meta[property='og:title']"),
          ogDescription: contents("meta[property='og:description']"),
          ogUrl: contents("meta[property='og:url']"),
          ogImage: contents("meta[property='og:image']"),
          ogImageWidth: contents("meta[property='og:image:width']"),
          ogImageHeight: contents("meta[property='og:image:height']"),
          ogImageAlt: contents("meta[property='og:image:alt']"),
          twitterCard: contents("meta[name='twitter:card']"),
          twitterTitle: contents("meta[name='twitter:title']"),
          twitterDescription: contents("meta[name='twitter:description']"),
          twitterImage: contents("meta[name='twitter:image']"),
          twitterImageAlt: contents("meta[name='twitter:image:alt']"),
        },
        jsonLd: Array.from(
          document.querySelectorAll<HTMLScriptElement>("script[type='application/ld+json']"),
          (element) => element.textContent ?? "",
        ),
        internalLinks: Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"), (element) => ({
          href: element.href,
          rel: element.rel,
        })),
        videos: Array.from(document.querySelectorAll<HTMLVideoElement>("video"), (video) => ({
          poster: video.poster,
          sources: [
            ...(video.src ? [video.src] : []),
            ...Array.from(video.querySelectorAll<HTMLSourceElement>("source[src]"), (source) => source.src),
          ],
          tracks: Array.from(video.querySelectorAll<HTMLTrackElement>("track[src]"), (track) => ({
            kind: track.kind,
            src: track.src,
            srclang: track.srclang,
          })),
        })),
        publicVideoLinks: Array.from(document.querySelectorAll<HTMLAnchorElement>("a[href]"), (element) => element.href)
          .filter((href) => /\.(?:m4v|mov|mp4|webm)(?:[?#]|$)/i.test(href)),
        transcriptText:
          (
            document.querySelector<HTMLElement>(
              "[data-video-transcript], #video-transcript, .video-transcript, [itemprop='transcript']",
            ) ??
            Array.from(document.querySelectorAll<HTMLElement>("h2, h3")).find(
              (heading) => heading.textContent?.trim().toLocaleLowerCase("en-US") === "transcript",
            )?.parentElement
          )?.innerText ?? "",
        analytics: Array.from(
          document.querySelectorAll<HTMLElement>("[data-analytics-event], [data-analytics-copy-event]"),
          (element) => ({
            event: element.getAttribute("data-analytics-event"),
            copyEvent: element.getAttribute("data-analytics-copy-event"),
            placement: element.getAttribute("data-analytics-placement"),
            attributes: Array.from(element.attributes, (attribute) => attribute.name).filter((name) =>
              name.startsWith("data-analytics-"),
            ),
          }),
        ),
      };
    }, path);
    snapshots.push(snapshot);

    expect(snapshot.title, `${path} title`).not.toBe("");
    expect(snapshot.descriptions, `${path} description count`).toHaveLength(1);
    expect(normalize(snapshot.descriptions[0]), `${path} description`).not.toBe("");
    expect(snapshot.h1s, `${path} H1 count`).toHaveLength(1);
    expect(normalize(snapshot.h1s[0]), `${path} H1`).not.toBe("");
    expect(snapshot.canonicals, `${path} canonical count`).toHaveLength(1);
    expect(snapshot.robots, `${path} robots count`).toHaveLength(1);
    expect(snapshot.robots[0], `${path} robots policy`).toBe(robotsDirective(path));
    expect(snapshot.keywords, `${path} must not emit the ignored meta-keywords tag`).toEqual([]);

    const canonical = new URL(snapshot.canonicals[0]);
    expect(canonical.search, `${path} canonical query`).toBe("");
    expect(canonical.hash, `${path} canonical fragment`).toBe("");
    if (path !== "/404.html") expect(canonical.pathname, `${path} canonical path`).toBe(path);
    if (canonical.hostname !== "localhost" && canonical.hostname !== "127.0.0.1") {
      expect(canonical.protocol, `${path} non-local canonical scheme`).toBe("https:");
    }

    const indexable = isIndexablePath(path);
    expect(snapshot.robots[0].includes("noindex"), `${path} index boundary`).toBe(!indexable);
    if (indexable) {
      // Deliberately low, repository-specific empty/template regression floor.
      expect(words(snapshot.mainText).length, `${path} unexpectedly thin rendered main content`).toBeGreaterThanOrEqual(
        45,
      );
      const intent = intentFor(path);
      expect(intent, `${path} has no declared search intent`).toBeTruthy();
      const visible = new Set(
        words([snapshot.title, snapshot.descriptions[0], snapshot.h1s[0], snapshot.mainText].join(" ")),
      );
      const intentTerms = significantWords(
        [intent!.primary_intent, ...intent!.supporting_concepts].join(" "),
      );
      const covered = [...intentTerms].filter((term) => visible.has(term));
      // Exact landing-page intents are individually authored and must cover
      // multiple declared concepts. Pattern intents intentionally span very
      // different guides/references, so one substantive concept is enough to
      // prove membership without forcing keyword repetition.
      const requiredCoverage = intentPolicy.pages[path] ? Math.min(2, intentTerms.size) : Math.min(1, intentTerms.size);
      expect(covered.length, `${path} visible copy does not substantiate its declared intent`).toBeGreaterThanOrEqual(
        requiredCoverage,
      );
    }

    const social = snapshot.social;
    for (const [name, values] of Object.entries(social)) {
      expect(values, `${path} ${name} count`).toHaveLength(1);
      expect(normalize(values[0]), `${path} ${name}`).not.toBe("");
    }
    expect(social.ogType[0], `${path} Open Graph type`).toMatch(/^(website|article)$/);
    expect(social.ogTitle[0]).toBe(snapshot.title);
    expect(social.twitterTitle[0]).toBe(snapshot.title);
    expect(social.ogDescription[0]).toBe(snapshot.descriptions[0]);
    expect(social.twitterDescription[0]).toBe(snapshot.descriptions[0]);
    expect(social.ogUrl[0]).toBe(snapshot.canonicals[0]);
    expect(social.twitterCard[0]).toBe("summary_large_image");
    expect(social.twitterImage[0]).toBe(social.ogImage[0]);
    expect(social.twitterImageAlt[0]).toBe(social.ogImageAlt[0]);
    expect(social.ogImageWidth[0]).toBe("1200");
    expect(social.ogImageHeight[0]).toBe("630");
    const socialImage = new URL(social.ogImage[0]);
    expect(socialImage.origin).toBe(canonical.origin);
    if (!checkedSocialImages.has(socialImage.pathname)) {
      const response = await page.request.get(socialImage.pathname);
      expect(response.status(), `${path} social image ${socialImage.pathname}`).toBe(200);
      checkedSocialImages.add(socialImage.pathname);
    }

    const parsedJsonLd: Array<Record<string, unknown>> = [];
    for (const raw of snapshot.jsonLd) {
      let block: Record<string, unknown>;
      try {
        block = JSON.parse(raw) as Record<string, unknown>;
      } catch (error) {
        throw new Error(`${path} contains invalid JSON-LD: ${String(error)}`);
      }
      parsedJsonLd.push(block);
      expect(block["@context"], `${path} JSON-LD context`).toBe("https://schema.org");
      expect(typeof block["@type"], `${path} JSON-LD root type`).toBe("string");

      const keys = collectJsonKeys(block);
      const types = collectJsonTypes(block);
      for (const key of ["aggregateRating", "offers", "potentialAction", "review"]) {
        expect(keys.has(key), `${path} JSON-LD contains unsupported/fabricated ${key}`).toBe(false);
      }
      for (const type of ["Organization", "SearchAction", "SoftwareApplication"]) {
        expect(types.has(type), `${path} JSON-LD contains unsupported/fabricated ${type}`).toBe(false);
      }

      if (typeof block.url === "string") expect(block.url, `${path} JSON-LD URL`).toBe(snapshot.canonicals[0]);
      if (typeof block.headline === "string") {
        expect(comparable(block.headline), `${path} JSON-LD headline/H1 parity`).toBe(
          comparable(snapshot.h1s[0]),
        );
      }
      if (
        typeof block.description === "string" &&
        (block["@type"] === "Article" || block["@type"] === "TechArticle")
      ) {
        expect(comparable(block.description), `${path} JSON-LD/meta description parity`).toBe(
          comparable(snapshot.descriptions[0]),
        );
      } else if (typeof block.description === "string") {
        const descriptionTerms = significantWords(block.description);
        const visibleWords = new Set(words(snapshot.pageText));
        const visibleTerms = [...descriptionTerms].filter((term) => visibleWords.has(term));
        expect(
          visibleTerms.length,
          `${path} JSON-LD description is not substantiated by visible copy`,
        ).toBeGreaterThanOrEqual(Math.min(3, descriptionTerms.size));
      }
      if (typeof block.datePublished === "string") {
        expect(block.datePublished, `${path} JSON-LD published date`).toMatch(/^\d{4}-\d{2}-\d{2}$/);
        expect(
          await page.locator(`time[datetime="${block.datePublished}"]`).count(),
          `${path} JSON-LD date must be visible`,
        ).toBeGreaterThan(0);
      }
      if (block["@type"] === "BreadcrumbList") {
        const items = block.itemListElement as Array<Record<string, unknown>>;
        expect(items.length, `${path} breadcrumb depth`).toBeGreaterThanOrEqual(2);
        items.forEach((item, index) => {
          expect(item.position, `${path} breadcrumb position`).toBe(index + 1);
          expect(typeof item.name, `${path} breadcrumb name`).toBe("string");
          expect(comparable(snapshot.pageText)).toContain(comparable(String(item.name)));
          expect(() => new URL(String(item.item))).not.toThrow();
        });
        expect(items.at(-1)?.item, `${path} final breadcrumb URL`).toBe(snapshot.canonicals[0]);
      }
      if (block.author && typeof block.author === "object") {
        const author = block.author as Record<string, unknown>;
        expect(typeof author.name, `${path} structured author name`).toBe("string");
        expect(comparable(snapshot.pageText), `${path} structured author must be visible`).toContain(
          comparable(String(author.name)),
        );
      }
    }

    const videoObjects = parsedJsonLd.flatMap((block) => jsonObjectsOfType(block, "VideoObject"));
    const hasPublicVideo = snapshot.videos.length > 0 || snapshot.publicVideoLinks.length > 0;
    if (!hasPublicVideo) {
      expect(videoObjects, `${path} must not emit stale VideoObject metadata`).toEqual([]);
      expect(snapshot.publicVideoLinks, `${path} must not emit a stale public video link`).toEqual([]);
    } else {
      expect(snapshot.videos.length, `${path} public video needs a visible video player`).toBeGreaterThan(0);
      expect(videoObjects.length, `${path} public video needs VideoObject metadata`).toBeGreaterThan(0);
      expect(
        words(snapshot.transcriptText).length,
        `${path} public video needs a substantive same-page visible transcript`,
      ).toBeGreaterThanOrEqual(50);

      const pageVideoSources = new Set(snapshot.videos.flatMap(({ sources }) => sources));
      const pagePosters = new Set(snapshot.videos.map(({ poster }) => poster).filter(Boolean));
      for (const video of snapshot.videos) {
        const captionTracks = video.tracks.filter(({ kind }) => kind === "captions" || kind === "subtitles");
        expect(captionTracks.length, `${path} public video needs captions/subtitles`).toBeGreaterThan(0);
        for (const track of captionTracks) {
          expect(track.srclang, `${path} caption track language`).not.toBe("");
          expect((await page.request.get(new URL(track.src).pathname)).status(), `${path} caption track`).toBe(200);
        }
      }
      for (const object of videoObjects) {
        expect(object.name, `${path} VideoObject name`).toBeTruthy();
        expect(object.uploadDate, `${path} VideoObject uploadDate`).toMatch(/^\d{4}-\d{2}-\d{2}/);
        expect(object.thumbnailUrl, `${path} VideoObject thumbnailUrl`).toBeTruthy();
        const thumbnails = (
          Array.isArray(object.thumbnailUrl) ? object.thumbnailUrl : [object.thumbnailUrl]
        ).map(String);
        expect(
          thumbnails.some((thumbnail) => pagePosters.has(thumbnail)),
          `${path} player poster/VideoObject thumbnail parity`,
        ).toBe(true);
        expect(object.contentUrl, `${path} VideoObject contentUrl`).toBeTruthy();
        expect(pageVideoSources.has(String(object.contentUrl)), `${path} player/VideoObject content URL parity`).toBe(
          true,
        );
      }
    }

    for (const item of snapshot.analytics) {
      expect(
        Number(item.event !== null) + Number(item.copyEvent !== null),
        `${path} analytics marker must name exactly one event`,
      ).toBe(1);
      const name = item.event ?? item.copyEvent;
      expect(allowedEvents.has(name!), `${path} analytics event ${name}`).toBe(true);
      expect(item.placement, `${path} analytics placement`).not.toBeNull();
      expect(allowedPlacements.has(item.placement!), `${path} analytics placement ${item.placement}`).toBe(true);
      expect(item.attributes.sort(), `${path} analytics attributes`).toEqual(
        item.event
          ? ["data-analytics-event", "data-analytics-placement"]
          : ["data-analytics-copy-event", "data-analytics-placement"],
      );
    }
  }

  const indexable = snapshots.filter(({ path }) => isIndexablePath(path));
  for (const field of ["title", "description", "h1"] as const) {
    const seen = new Map<string, string>();
    for (const snapshot of indexable) {
      const value =
        field === "title"
          ? snapshot.title
          : field === "description"
            ? snapshot.descriptions[0]
            : snapshot.h1s[0];
      const key = comparable(value);
      expect(seen.get(key), `duplicate ${field}: ${snapshot.path} and ${seen.get(key)}`).toBeUndefined();
      seen.set(key, snapshot.path);
    }
  }

  const canonicalOrigins = new Set(indexable.map(({ canonicals }) => new URL(canonicals[0]).origin));
  expect(canonicalOrigins.size, "all indexable pages must share one canonical origin").toBe(1);
  const fingerprints = new Map<string, string>();
  const pageShingles = indexable.map((snapshot) => ({
    path: snapshot.path,
    value: shingles(snapshot.mainText),
  }));
  for (const snapshot of indexable) {
    const fingerprint = comparable(snapshot.mainText);
    expect(
      fingerprints.get(fingerprint),
      `duplicate rendered public content: ${snapshot.path} and ${fingerprints.get(fingerprint)}`,
    ).toBeUndefined();
    fingerprints.set(fingerprint, snapshot.path);
  }
  for (let left = 0; left < pageShingles.length; left += 1) {
    for (let right = left + 1; right < pageShingles.length; right += 1) {
      expect(
        jaccard(pageShingles[left].value, pageShingles[right].value),
        `suspiciously repetitive public pages: ${pageShingles[left].path} and ${pageShingles[right].path}`,
      ).toBeLessThan(0.92);
    }
  }

  const inbound = new Map(indexable.map(({ path }) => [path, new Set<string>()]));
  for (const source of indexable) {
    const acceptedOrigins = new Set([source.runtimeOrigin, new URL(source.canonicals[0]).origin]);
    for (const link of source.internalLinks) {
      const url = new URL(link.href);
      if (!acceptedOrigins.has(url.origin) || link.rel.split(/\s+/).includes("nofollow")) continue;
      const target = normalizePathname(url.pathname);
      if (target && inbound.has(target) && target !== source.path) {
        inbound.get(target)!.add(source.path);
      }
    }
  }
  for (const target of indexable.map(({ path }) => path).filter((path) => path !== "/")) {
    expect(
      inbound.get(target)?.size ?? 0,
      `${target} is an orphan: no crawlable internal inbound link from another indexable page`,
    ).toBeGreaterThan(0);
  }
});

test("sitemap is the exact canonical indexable set with truthful lastmod fields", async ({ request }) => {
  const indexResponse = await request.get("/sitemap-index.xml");
  expect(indexResponse.status()).toBe(200);
  const indexXml = await indexResponse.text();
  const childSitemaps = [...indexXml.matchAll(/<sitemap>([\s\S]*?)<\/sitemap>/g)]
    .map((match) => xmlValue(match[1], "loc"))
    .filter((value): value is string => Boolean(value));
  expect(childSitemaps.length).toBeGreaterThan(0);

  const entries: Array<{ loc: string; lastmod: string | undefined }> = [];
  for (const sitemap of childSitemaps) {
    const response = await request.get(new URL(sitemap).pathname);
    expect(response.status(), sitemap).toBe(200);
    const xml = await response.text();
    expect(xml).not.toMatch(/<(changefreq|priority)>/);
    for (const match of xml.matchAll(/<url>([\s\S]*?)<\/url>/g)) {
      const loc = xmlValue(match[1], "loc");
      if (loc) entries.push({ loc, lastmod: xmlValue(match[1], "lastmod") });
    }
  }

  const expectedPaths = PAGES.filter((path) => isIndexablePath(path)).sort();
  const actualPaths = entries.map(({ loc }) => new URL(loc).pathname).sort();
  expect(actualPaths).toEqual(expectedPaths);
  expect(new Set(entries.map(({ loc }) => loc)).size).toBe(entries.length);
  expect(new Set(entries.map(({ loc }) => new URL(loc).origin)).size).toBe(1);

  const tomorrow = Date.now() + 24 * 60 * 60 * 1_000;
  for (const { loc, lastmod } of entries) {
    const url = new URL(loc);
    expect(url.search, `${loc} sitemap query`).toBe("");
    expect(url.hash, `${loc} sitemap fragment`).toBe("");
    expect(url.pathname, `${loc} canonical slash form`).toMatch(/\/$/);
    expect(lastmod, `${loc} missing lastmod`).toMatch(/^\d{4}-\d{2}-\d{2}(?:T00:00:00\.000Z)?$/);
    expect(Date.parse(lastmod!), `${loc} invalid lastmod`).not.toBeNaN();
    expect(Date.parse(lastmod!), `${loc} future lastmod`).toBeLessThan(tomorrow);
  }
});

test("robots policy separates search discovery from training crawlers and names the canonical sitemap", async ({
  request,
}) => {
  const response = await request.get("/robots.txt");
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toContain("text/plain");
  const body = await response.text();
  expect(body).not.toMatch(/^\s*Noindex:/im);
  expect(body).toMatch(/User-agent: OAI-SearchBot\s+Allow: \//);
  expect(body).toMatch(/User-agent: PerplexityBot\s+Allow: \//);
  expect(body).toMatch(/User-agent: GPTBot\s+Disallow: \//);
  expect(body).toMatch(/User-agent: Google-Extended\s+Disallow: \//);
  expect(body).toMatch(/User-agent: CCBot\s+Disallow: \//);
  expect(body).toMatch(/User-agent: \*\s+Allow: \//);
  expect(body).toMatch(/Sitemap: https?:\/\/[^/\s]+\/sitemap-index\.xml/);
  expect(Object.keys(intentPolicy.noindex).sort()).toEqual(["/404.html", "/docs/search/"]);
});

test("analytics defaults strip query data, honor local opt-out, and do not emit custom events", async ({ page }) => {
  await page.goto("/?utm_source=linkedin&utm_campaign=oss-launch&email=person%40example.test");
  const result = await page.evaluate(() => {
    const queue = ((window as unknown as { vaq?: ArrayLike<unknown>[] }).vaq ?? []).map((entry) =>
      Array.from(entry),
    );
    const beforeSend = queue.find((entry) => entry[0] === "beforeSend")?.[1];
    if (typeof beforeSend !== "function") throw new Error("Vercel beforeSend hook was not registered");
    const sanitize = beforeSend as (event: { url: string }) => { url: string } | null;
    const sanitized = sanitize({ url: location.href });
    const eventCountBefore = queue.filter((entry) => entry[0] === "event").length;
    const target = document.querySelector<HTMLElement>("[data-analytics-event]");
    if (!target) throw new Error("no analytics-decorated control exists");
    addEventListener("click", (event) => event.preventDefault(), { capture: true, once: true });
    target.click();
    const afterQueue = ((window as unknown as { vaq?: ArrayLike<unknown>[] }).vaq ?? []).map((entry) =>
      Array.from(entry),
    );
    const eventCountAfter = afterQueue.filter((entry) => entry[0] === "event").length;
    localStorage.setItem("irrevon-analytics-opt-out", "1");
    const optedOut = sanitize({ url: location.href });
    return { sanitizedUrl: sanitized?.url ?? null, eventCountBefore, eventCountAfter, optedOut };
  });

  expect(result.sanitizedUrl).not.toBeNull();
  expect(new URL(result.sanitizedUrl!).search).toBe("");
  expect(result.eventCountAfter).toBe(result.eventCountBefore);
  expect(result.optedOut).toBeNull();
});

test("privacy page exposes a working local measurement preference", async ({ page }) => {
  await page.goto("/privacy/");
  const button = page.locator("#analytics-choice");
  const status = page.locator("#analytics-choice-status");
  await expect(button).toHaveText("Disable future site measurement");
  await expect(status).toContainText("allowed");

  await button.click();
  await expect(button).toHaveText("Enable site measurement");
  await expect(status).toContainText("disabled");
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("irrevon-analytics-opt-out")))
    .toBe("1");

  await page.reload();
  await expect(button).toHaveText("Enable site measurement");
  await button.click();
  await expect(button).toHaveText("Disable future site measurement");
  await expect
    .poll(() => page.evaluate(() => localStorage.getItem("irrevon-analytics-opt-out")))
    .toBeNull();
});
