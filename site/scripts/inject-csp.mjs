// Injects a per-page <meta http-equiv="Content-Security-Policy"> into every
// built HTML page, with script-src hashes COMPUTED from the page's actual
// inline scripts — hand-maintained hashes rot; computed ones cannot. Runs
// after `astro build` + pagefind, so it hashes the final markup. A new
// inline script without a build-computed hash simply fails to execute AND
// fails the CSP e2e — exactly the discipline we want for JS creep.
//
// Meta-CSP limits, stated honestly: it cannot carry frame-ancestors,
// report-uri, or sandbox — those need real response headers, which GitHub
// Pages cannot set. The full when-we-have-an-edge header set lives in
// site/docs/headers-spec.md.
//
// script-src carries 'self' on every page: the Vercel Web Analytics /
// Speed Insights loaders (/_vercel/.../script.js, ADR-0029) are same-origin
// platform-served files a build cannot hash. Inline scripts still require the
// computed hashes ('self' never permits inline). Docs pages additionally get
// 'wasm-unsafe-eval' for Pagefind's WASM; Pagefind fetches and the telemetry
// beacons both ride connect-src 'self' — everything is same-origin by
// construction.
//
// Usage: node scripts/inject-csp.mjs [dist-dir]

import { createHash } from "node:crypto";
import { readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const dist = process.argv[2] ?? join(here, "..", "dist");

function htmlFiles(dir) {
  const out = [];
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    if (e.isDirectory()) out.push(...htmlFiles(join(dir, e.name)));
    else if (e.name.endsWith(".html")) out.push(join(dir, e.name));
  }
  return out;
}

const SCRIPT_RE = /<script(?![^>]*\bsrc=)([^>]*)>([\s\S]*?)<\/script>/g;

let pages = 0;
for (const file of htmlFiles(dist)) {
  let html = readFileSync(file, "utf8");
  // Idempotent: strip any previously injected policy first.
  html = html.replace(/<meta http-equiv="Content-Security-Policy"[^>]*>\n?/g, "");

  const hashes = new Set();
  for (const m of html.matchAll(SCRIPT_RE)) {
    const attrs = m[1];
    // JSON-LD data blocks never execute; script-src does not gate them.
    if (/type="application\/ld\+json"/.test(attrs)) continue;
    hashes.add(`'sha256-${createHash("sha256").update(m[2]).digest("base64")}'`);
  }

  const isDocs = /\/docs\//.test(file.replace(dist, ""));
  const scriptSrc = [
    "'self'",
    ...(isDocs ? ["'wasm-unsafe-eval'"] : []),
    ...[...hashes].sort(),
  ];
  const policy = [
    "default-src 'none'",
    `script-src ${scriptSrc.length ? scriptSrc.join(" ") : "'none'"}`,
    "style-src 'self' 'unsafe-inline'",
    "img-src 'self' data:",
    "font-src 'self'",
    "connect-src 'self'",
    "base-uri 'none'",
    "form-action 'self'",
  ].join("; ");

  html = html.replace(
    /(<meta name="viewport"[^>]*>)/,
    `$1<meta http-equiv="Content-Security-Policy" content="${policy}">`,
  );
  writeFileSync(file, html);
  pages += 1;
}
console.log(`inject-csp: policy injected into ${pages} pages`);
