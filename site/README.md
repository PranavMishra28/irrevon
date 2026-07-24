# site/ — the public marketing + discovery site

The Irrevon public site: the original six pages plus the discovery surface added by
the site-expansion cycle (docs section with drift-gated rendered repository documents,
searchable via self-hosted Pagefind; the interactive recorded demo; research,
changelog, roadmap, install; full SEO/metadata). **Configured for Vercel at the origin
root** by owner directive ([ADR-0027](../docs/decisions/0027-site-vercel-deploy.md));
deploys remain human-gated acts, never CI-triggered (see [Deploy](#deploy) below; the
gate-reconciliation record lives in [docs/review-queue.md](../docs/review-queue.md)).
The configured production deployment was paused when checked on 2026-07-24 and
must not be described as live until the owner restores it and verifies the
launch checklist in `docs/discoverability.md`.
The site never ships in the Python wheel (ADR-0018) and shares no build with `web/`.

## Page inventory

| Route | Page |
|---|---|
| `/` | Home — problem, recorded artifact, beat-10 hero poster + step-through link, three mechanisms, non-guarantees, bench teaser, get-started |
| `/platform` | Engine (honest title) — components, implemented-today strip, capability declaration, roadmap boundary |
| `/how-it-works` | Mechanism — re-synthesis failure, identity, state model, the recorded ambiguous case (+ link into /demo), tiers, prior art |
| `/benchmark` | IrrevonBench — DRAFT banner, credibility controls, baseline ladder, kill criterion, metrics, integrity (+ reproduction-guide link) |
| `/security` | Security & trust — trust boundary, data posture, supply chain, non-claims, this site's own headers (+ headers-spec link) |
| `/demo` | **The One-Way Seat** — the recorded flagship run as a step-driven 12-beat sequence + B5 contrast lane (anti-fabrication-gated) |
| `/docs/` | Docs landing — guides, rendered reference library, search box, canonical link-only block (master doc + pinned hash) |
| `/docs/<guide>/` | Nine guides: getting-started, CLI reference (generated from `--help`), integration, adapter development, benchmark reproduction (NO RESULTS YET), architecture, ambiguous API outcomes, idempotency versus reconciliation, and workflow/outbox/saga boundaries |
| `/docs/reference/<slug>/` | Manifest-selected, provenance-stamped repository documents (RFCs, benchmark and operations guides, contracts, governance, and ADRs) |
| `/docs/search/` | Pagefind search (docs-scoped, loads on gesture, no-JS fallback) |
| `/research/` (+2 posts, `/research/rss.xml`) | Preregistration story + prior-art credit; explicit no-preprint statement |
| `/changelog` | Computed from `git tag --list` at build — honest empty state (zero tags) |
| `/roadmap` | Phases parsed from the rendered execution plan; no-dates banner |
| `/install` | Works-today from source; planned distribution future-tense in a PLANNED block |
| `/status`, `/privacy`, `/contributing`, `/licensing` | Launch status, data posture, contribution path, and legal/attribution guidance |
| `/404` | Not-found page (Vercel serves `404.html` for unmatched routes) |

Use Cases, About/Company, Contact, and any demo-request page remain **omitted, not
stubbed**. Navigation: Engine · How it works · Demo · Benchmark · Docs · Research ·
Install (7 slots); Status, Privacy, Contributing, Licensing, Security, Changelog, and
Roadmap live in the footer.

## Truth discipline

- **Claims registry:** every key claim lives in
  [`src/data/claims.ts`](src/data/claims.ts); pages cite by id via the
  `Source` component; [`CLAIMS.md`](CLAIMS.md) is generated (`pnpm claims:md`,
  `--check` gates drift). Guide/research frontmatter `claims` arrays are
  zod-validated against the registry — an unknown id fails the build.
- **Three-badge system** (`Badge.astro`): `RECORDED ARTIFACT`, `CONCEPTUAL`,
  `PREREGISTERED METHODOLOGY — NO RESULTS YET`.
- **Rendered docs cannot fork the truth:** `scripts/sync-docs.mjs` +
  `docs-manifest.json` copy repository documents into the content collection with
  `sourceSha256` provenance frontmatter (rendered banner on every page); `--check`
  fails CI on any byte drift. The master doc is deliberately link-only (its pinned
  hash is named on the docs landing). The CLI reference is captured verbatim from
  `uv run irrevon --help` (`scripts/sync-cli-reference.mjs`; tamper-evidence fallback
  where uv is absent).
- **The demo cannot fabricate:** `/demo` renders every number/id/status from
  `src/data/demo/` (synced + drift-gated from `web/fixtures/canonical` by
  `scripts/sync-demo.mjs`); `e2e/demo.spec.ts` asserts the rendered HTML against the
  same JSON, including a 64-hex allowlist.
- **What cannot appear anywhere:** pricing, customers, testimonials, SLAs, benchmark
  numbers, uncited numbers, any old-name install literal (e2e-banned), any
  package-index command outside the PLANNED block, "exactly-once"/"rollback"
  unqualified, fake forms, employer identifiers.

## Architecture

- Astro `7.1.0` (exact pin), static output, `passthroughImageService`. Markdown via
  the native Sätteri processor with two local plugins
  (`scripts/satteri-repo-links.mjs`): repo-relative link rewriting (rendered docs
  never embed a repo URL — the build resolves links to rendered siblings or GitHub)
  and a11y fixes (scrollable tables/pre get `tabindex`, GFM checkboxes render as
  typographic marks). Syntax highlighting is off by design (plain mono matches the
  site register; cannot fail contrast).
- **JS discipline.** No fetched scripts on any page except two documented lanes: the
  same-origin Vercel Web Analytics + Speed Insights loaders on every page
  (`/_vercel/…/script.js` — owner-enabled, [ADR-0029](../docs/decisions/0029-site-vercel-analytics.md);
  cookie-free, same-origin transport to a Vercel processor) and the docs-after-gesture
  Pagefind bundle (`dist/pagefind/`, built post-build, loads only on focus/input).
  The shared inline code covers theme behavior, query redaction, a local telemetry
  opt-out, and an optional fixed event/placement allowlist; conversion events and
  UTM retention are disabled unless the owner enables their separate plan-aware
  build gates. The `/demo` island remains ≤8 KB. Budget e2e runs two lanes over a
  dist-derived page inventory and pins fetched scripts to exactly those two
  telemetry paths plus gesture-loaded Pagefind.
- **SEO/metadata:** `@astrojs/sitemap` (+`sitemap-index.xml`), `robots.txt` endpoint,
  canonical + OG/Twitter cards per page (committed OG PNGs rendered from
  `og/template.svg` by `scripts/build-og.mjs`, drift-gated via `og/manifest.json`),
  JSON-LD (`SoftwareSourceCode`/`WebSite` on Home, `Article` on
  research, `TechArticle`+`BreadcrumbList` on docs — never `SoftwareApplication`,
  never offers/ratings). `search-intents.json` assigns every indexable route a
  human intent; browser gates enforce unique metadata/H1s, exact sitemap and
  `lastmod`, structured-data/visible-content parity, no thin/orphan/duplicate
  pages, crawler policy, social cards, and the absence of stale video markup.
  Search crawlers are allowed while named training crawlers follow the reviewed
  separate policy. Vercel previews are `noindex,nofollow` with a disallow-all
  `robots.txt`; production verification values are environment-provided.
- **Security headers:** real response headers ship from [`vercel.json`](vercel.json)
  (frame-ancestors, HSTS, nosniff, permissions/referrer policy, COOP, cache rules) —
  the applied form of [`docs/headers-spec.md`](docs/headers-spec.md), which keeps the
  rationale. `scripts/inject-csp.mjs` additionally injects a per-page meta CSP with
  build-computed inline script hashes (docs pages add `'self' 'wasm-unsafe-eval'` for
  Pagefind) — a static header cannot carry per-page hashes; meta cannot carry
  frame-ancestors; together they cover both.
- **Base-path safe, served at `/`:** internal links via `src/lib/url.ts`; markdown
  site-absolute links get the base at build; sitemap/RSS/OG URLs derive from the
  deploy-provided origin (`SITE_ORIGIN`, or the Vercel production URL on platform
  builds). The repository URL is deployment-provided (`SITE_REPO_URL` env, Vercel git
  metadata, or the local git remote — never committed).
- **Vendored identity, drift-checked:** tokens + fonts synced from `web/`
  (`--check` in `pnpm check`); domain icons + the One-Way Seat stage are original
  in-house geometry — provenance ledger in [`ASSETS.md`](ASSETS.md).

## Dependency register (per-dep justification)

| Package | Why |
|---|---|
| `astro` 7.1.0 | The static site framework (zero-JS-by-default; deploy-provided `site` origin) |
| `@astrojs/sitemap` 3.7.3 | First-party sitemap; URLs from the deploy-provided origin |
| `@astrojs/rss` 4.0.19 | First-party RSS for /research |
| `@astrojs/markdown-satteri` 0.3.4 | Explicit pin of Astro 7's own markdown processor so the local mdast/hast plugins import a declared dependency |
| `pagefind` 1.5.2 (dev) | Post-build static search index + self-hosted UI; MIT; loads only on docs gesture |
| `@astrojs/check` 0.9.9 / `typescript` 5.9.3 | `astro check` gate |
| `@playwright/test` 1.61.1 | e2e gates + review screenshots + OG card rendering (no extra raster dep) |
| `@axe-core/playwright` 4.12.1 | WCAG 2.2 AA scans as test failures |

pnpm hardening unchanged: `allowBuilds` all-false, `minimumReleaseAge` 10080,
`trustPolicy: no-downgrade`, `blockExoticSubdeps`, exact pins, frozen lockfile.
Narrow reviewed exclusions only (rationale inline in
[`pnpm-workspace.yaml`](pnpm-workspace.yaml)): `trustPolicyExclude`
`chokidar@4.0.3`; `minimumReleaseAgeExclude` for the `fast-xml-parser` /
`fast-uri` security patches (droppable once their 7-day windows pass).

## Commands

```bash
export ASTRO_TELEMETRY_DISABLED=1
pnpm install            # Node 24 (.nvmrc), pnpm 11
pnpm dev                # local dev (search + CSP exist only in built output)
pnpm check              # astro check + every drift gate: tokens, fonts, claims,
                        # docs sync, CLI reference, demo artifacts, OG cards
pnpm build              # astro build && pagefind && inject-csp; writes the
                        # deploy-only IndexNow key file only when INDEXNOW_KEY exists
pnpm test               # Playwright checks: axe (every page × both themes incl.
                        # /demo stepped states), keyboard, no-JS, links, budgets
                        # (two lanes), search, demo anti-fabrication, install
                        # honesty, SEO/CSP
pnpm shots              # every page at 1440/768/375 × light/dark (+ /demo
                        # reduced-motion beats) -> shots/
pnpm sync:docs | sync:cli | sync:demo | og:build   # regenerate synced artifacts
```

The owner-operated search, crawler, campaign, IndexNow, webmaster, analytics,
GitHub-traffic, and video-publication procedure is
[`docs/discoverability.md`](../docs/discoverability.md). `public/llms.txt` is an
optional navigation aid only; it is not a ranking, crawler, or licensing control.

## Deploy

The site deploys to Vercel as a **static upload of the built `dist/` output** — the
platform serves files and headers, nothing builds or runs server-side
([ADR-0027](../docs/decisions/0027-site-vercel-deploy.md)). A deploy is an
owner-directed act, never CI-triggered:

```bash
SITE_ORIGIN=https://<production-host> SITE_REPO_URL=<repo-url> pnpm build
# then upload dist/ (plus vercel.json at the upload root) as a Vercel
# production deployment — e.g. `vercel deploy --prod` from a directory
# containing exactly that tree, or the Vercel MCP/API equivalent.
```

`vercel.json` carries the response headers and cache rules (the applied form of
[`docs/headers-spec.md`](docs/headers-spec.md)) and `trailingSlash: true` (canonical
URLs end in `/`, matching the sitemap). The origin and repository URL are
deployment-provided at build time — committed files never carry either. (The current
Vercel project equivalently builds on the platform via a small deployment-side script
that clones the repository with owner-provided access and runs the same `pnpm build`; that script lives
in the deployment, not the repo, because it must carry the deploy-provided values.)
Google/Bing verification values and the optional IndexNow key belong in protected
production build variables, never a committed file or pasted command history.

`SITE_ENABLE_CUSTOM_EVENTS=1` is optional and only appropriate on Vercel Pro or
Enterprise. `SITE_ENABLE_UTM_ANALYTICS=1` is separate and only appropriate with
Web Analytics Plus or Enterprise. Omitting either value is the safe functional
fallback. A deploy should be followed by the dry-run-first IndexNow procedure in
the discoverability runbook; submission is never part of CI.

## Release gates

- Build and type checks: `pnpm check && pnpm build`.
- Browser checks: `pnpm test`; review screenshots: `pnpm shots`.
- JS weight: every page remains under the enforced ≤10 KB inline-script budget.
  All pages may fetch exactly the two permitted same-origin Vercel telemetry
  loaders. Docs pages may additionally fetch same-origin `/pagefind/` assets
  only after a search gesture. Browser tests fail on any other fetched script
  or budget regression.
- Claims registry: every entry is source-mapped; `CLAIMS.md` is generated and
  drift-gated.

## Maintenance

- The rendered copies of pre-rename records (ADR-0023 and the review queue) quote the
  old product/package name as historical fact — those pages are the sanctioned,
  provenance-bannered exceptions in `e2e/install.spec.ts` and are allowlisted by any
  repo-wide old-name sweep (append-only history discipline).
- Workbench screenshots (`public/images/`) are captured from the running
  fixture-backed `web/` app — re-capture with `scripts/capture-workbench.mjs` after
  any workbench visual change, then re-run `pnpm sync:tokens`.
