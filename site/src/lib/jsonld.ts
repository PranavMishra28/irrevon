// JSON-LD builders. Deliberate ruling: Home remains SoftwareSourceCode;
// SoftwareApplication commonly invites offers/ratings this site must not fabricate.
// Nothing anywhere gets aggregateRating, offers, review, or an organization
// entity (none exists).
import { SITE_NAME, REPO_URL, repoDoc } from "../config";
import {
  PYPI_PROJECT_URL,
  RELEASED_AT,
  RELEASE_VERSION,
} from "./release-provenance";

type JsonLd = Record<string, unknown>;

export const softwareSourceCode = (siteUrl: URL, description: string): JsonLd => ({
  "@context": "https://schema.org",
  "@type": "SoftwareSourceCode",
  name: SITE_NAME,
  description,
  codeRepository: REPO_URL,
  license: repoDoc("LICENSE"),
  programmingLanguage: "Python",
  softwareVersion: RELEASE_VERSION,
  datePublished: RELEASED_AT?.slice(0, 10),
  downloadUrl: PYPI_PROJECT_URL,
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
