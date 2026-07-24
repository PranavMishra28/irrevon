import assert from "node:assert/strict";
import test from "node:test";
import {
  CRAWLER_RULES,
  isIndexablePath,
  normalizePathname,
  renderRobots,
  robotsDirective,
} from "./search-policy.mjs";

test("canonical pages remain indexable while search and error surfaces do not", () => {
  assert.equal(isIndexablePath("/"), true);
  assert.equal(isIndexablePath("/docs"), true);
  assert.equal(isIndexablePath("/docs/index.html"), true);
  assert.equal(isIndexablePath("/docs/search/"), false);
  assert.equal(isIndexablePath("/docs/search/index.html"), false);
  assert.equal(isIndexablePath("/404"), false);
  assert.equal(isIndexablePath("/404/"), false);
  assert.equal(isIndexablePath("/404.html"), false);
});

test("malformed and ambiguous paths fail closed", () => {
  for (const pathname of [
    "",
    "docs/",
    "/docs//guide/",
    "/docs/%2e%2e/private/",
    "/docs\\private/",
    "/docs/?q=secret",
    "/docs/#fragment",
    "/docs/\u0000",
  ]) {
    assert.equal(normalizePathname(pathname), null);
    assert.equal(isIndexablePath(pathname), false);
    assert.equal(robotsDirective(pathname), "noindex,nofollow");
  }
});

test("robots directives distinguish result surfaces from error documents", () => {
  assert.equal(
    robotsDirective("/docs/"),
    "index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1",
  );
  assert.equal(robotsDirective("/docs/search/"), "noindex,follow");
  assert.equal(robotsDirective("/404.html"), "noindex,nofollow");
});

test("robots output preserves the reviewed search-versus-training policy", () => {
  assert.deepEqual(
    CRAWLER_RULES.map(({ userAgent, directive }) => [userAgent, directive]),
    [
      ["OAI-SearchBot", "Allow"],
      ["PerplexityBot", "Allow"],
      ["GPTBot", "Disallow"],
      ["Google-Extended", "Disallow"],
      ["CCBot", "Disallow"],
      ["*", "Allow"],
    ],
  );
  assert.equal(
    renderRobots("https://irrevon.example/sitemap-index.xml"),
    [
      "User-agent: OAI-SearchBot",
      "Allow: /",
      "",
      "User-agent: PerplexityBot",
      "Allow: /",
      "",
      "User-agent: GPTBot",
      "Disallow: /",
      "",
      "User-agent: Google-Extended",
      "Disallow: /",
      "",
      "User-agent: CCBot",
      "Disallow: /",
      "",
      "User-agent: *",
      "Allow: /",
      "",
      "Sitemap: https://irrevon.example/sitemap-index.xml",
      "",
    ].join("\n"),
  );
});

test("robots output rejects noncanonical or non-HTTPS sitemap targets", () => {
  for (const sitemap of [
    "http://irrevon.example/sitemap-index.xml",
    "https://irrevon.example:443/sitemap-index.xml",
    "https://IRREVON.example/sitemap-index.xml",
    "https://irrevon.example/other.xml",
    "https://irrevon.example/sitemap-index.xml?token=secret",
  ]) {
    assert.throws(() => renderRobots(sitemap), /canonical HTTPS sitemap/);
  }
});

test("robots output permits only localhost for an HTTP development build", () => {
  assert.match(
    renderRobots("http://localhost:4977/sitemap-index.xml"),
    /Sitemap: http:\/\/localhost:4977\/sitemap-index\.xml/,
  );
});
