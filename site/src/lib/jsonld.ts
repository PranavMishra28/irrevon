// JSON-LD builders. Deliberate rulings: the project is a repository, not an
// installable app, so Home is SoftwareSourceCode (SoftwareApplication implies
// offers/ratings this site must not fabricate — revisit at first release).
// Nothing anywhere gets aggregateRating, offers, review, or an organization
// entity (none exists).
import { SITE_NAME, REPO_URL } from "../config";

type JsonLd = Record<string, unknown>;

export const softwareSourceCode = (siteUrl: URL): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  name: SITE_NAME,
  description:
    "A preregistered benchmark and reference reconciliation engine for irreversible AI-agent actions. Pre-release, open research; no license granted yet.",
  codeRepository: REPO_URL,
  programmingLanguage: "Python",
  url: siteUrl.toString(),
});

export const webSite = (siteUrl: URL, searchUrl: URL): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  url: siteUrl.toString(),
  potentialAction: {
    "@type": "SearchAction",
    target: {
      "@type": "EntryPoint",
      urlTemplate: `${searchUrl}?q={search_term_string}`,
    },
    "query-input": "required name=search_term_string",
  },
});

export const article = (opts: { title: string; description: string; url: URL; datePublished: string }): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "Article",
  headline: opts.title,
  description: opts.description,
  url: opts.url.toString(),
  datePublished: opts.datePublished,
  author: { "@type": "Person", name: `${SITE_NAME} maintainer` },
});

export const techArticle = (opts: { title: string; description: string; url: URL }): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "TechArticle",
  headline: opts.title,
  description: opts.description,
  url: opts.url.toString(),
});

export const breadcrumbs = (items: { name: string; url: URL }[]): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: items.map((item, i) => ({
    "@type": "ListItem",
    position: i + 1,
    name: item.name,
    item: item.url.toString(),
  })),
});
