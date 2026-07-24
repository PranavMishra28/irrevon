// JSON-LD builders. Deliberate rulings: the project is a repository, not an
// installable app, so Home is SoftwareSourceCode (SoftwareApplication implies
// offers/ratings this site must not fabricate — revisit at first release).
// Nothing anywhere gets aggregateRating, offers, review, or an organization
// entity (none exists).
import { SITE_NAME, REPO_URL, repoDoc } from "../config";

type JsonLd = Record<string, unknown>;

export const softwareSourceCode = (siteUrl: URL, description: string): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  name: SITE_NAME,
  description,
  codeRepository: REPO_URL,
  license: repoDoc("LICENSE"),
  programmingLanguage: "Python",
  url: siteUrl.toString(),
});

export const webSite = (siteUrl: URL): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  url: siteUrl.toString(),
});

export const article = (opts: { title: string; description: string; url: URL; datePublished: string }): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "Article",
  headline: opts.title,
  description: opts.description,
  url: opts.url.toString(),
  datePublished: opts.datePublished,
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
