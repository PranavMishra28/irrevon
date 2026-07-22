---
title: "Marketing site + discovery surface (`site/`) — public pages, gated deploy"
sourcePath: "docs/decisions/0025-site-discovery-surface.md"
sourceSha256: "c87db9615b0656edf703d4a0737d32b701f8b21bad4203f43473ca740066a0b4"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0025"
  status: "accepted (owner rebuild directive, 2026-07-21; number reserved by review-queue §3 item 21); decision items 4–5 (gated Pages deploy + Pages slot layout) superseded by ADR-0027"
  date: "2026-07-21"
  supersedes: "— (amends the scope of ADR-0018 §4.1 row 12's \"no brand site\" ruling; its $0 / no-domain / no-SaaS rulings stand)"
---

## Context

Review-queue §3 item 20 proposed the marketing-site ADR when the six-page `site/` package
landed at the 2026-07 consolidation; item 21 reserved id 0025 for it. The owner's rebuild
directive of 2026-07-21 ordered the site-expansion cycle (the discovery surface). This ADR
records both: the site package as the customer-facing surface, and the discovery surface
that grew it to 44 built pages. Deploy remains fully gated: the `site-deploy` workflow is
`workflow_dispatch`-only, Pages enablement is a human-only settings act, and the deploy
gate list lives in the review queue.

## Decision

1. **`site/` is the public marketing + discovery surface**: an Astro static package,
   zero-JS-by-default, identity vendored from the workbench tokens (drift-gated), claims
   registry with generated `CLAIMS.md` (drift-gated). It never ships in the Python wheel
   (ADR-0018) and shares no build with `web/`.
2. **The discovery surface** (site-expansion cycle): a docs section rendering repository
   documents byte-synced with `sourceSha256` provenance and drift gates (`sync-docs.mjs`);
   six guides; self-hosted Pagefind search (loads only on user gesture, same-origin);
   the recorded interactive 12-beat demo (`/demo`, anti-fabrication-gated against the
   synced artifact JSON); research (2 posts + RSS), computed-honest changelog, dateless
   roadmap, install page (works-today source path; packaged install future-tense inside a
   PLANNED block); full SEO/metadata (sitemap, canonical, OG pipeline, JSON-LD as
   `SoftwareSourceCode`, never `SoftwareApplication`); per-page meta CSP with
   build-computed hashes.
3. **Truth discipline is load-bearing**: every key number/claim cites the registry or a
   synced artifact; rendered docs cannot fork the truth (byte drift fails CI); no pricing,
   customers, testimonials, SLAs, benchmark numbers, or install commands rendered as
   available-today.
4. **Deploy stays human-gated** (unchanged): dispatch-only workflow; Pages enablement,
   publication clearances, counsel name clearance, licensing, and the AM-21 Pages-slot
   amendment gate the first real deploy.
5. **Pages slot layout**: the site serves at `/`; the M8 rendered-docs plan moves under
   `/docs/` — the site's docs section supersedes the ADR-0018 M8 MkDocs plan (AM-21
   extension recorded in the review queue).

## Alternatives

- **No site until release** — rejected by the owner's directive; the discovery surface is
  buildable and testable now with deploy gated, and the claims discipline keeps it honest
  pre-release.
- **MkDocs for the docs surface (ADR-0018 M8 plan)** — superseded: the site's synced
  rendered-docs pipeline provides the same content with provenance banners and drift
  gates, in the shared Pages slot (AM-21 extension).
- **A JS-framework site** — rejected: zero-JS-by-default Astro matches the budget gates
  (≤10 KB inline, zero fetched scripts outside the documented docs/demo lanes).

## Consequences

- Gates: `make site-check` / `site-build` / `site-test` (astro check + all drift gates;
  build; Playwright a11y/keyboard/no-JS/links/budgets/search/anti-fabrication/SEO).
- CI carries conditional site jobs wired into the `ci-required` aggregator.
- The owner rulings still owed from item 20 remain open: (a) Book-a-Demo naming/presence,
  (b) public contact address vs "GitHub-issues-only", (c) DE-1 posture over `site/` work.

## Risks

- A deploy before the gate list closes would publish pre-clearance content — mitigated:
  dispatch-only workflow, human-only Pages enablement, the gate list in the review queue.
- Synced-docs staleness between sync runs — mitigated by the `--check` drift gates in
  `site-check` and CI.

## Reopen trigger

The first real deploy (forces the AM-21 ratification and the item-20 owner rulings); or a
custom domain decision (changes robots.txt/CSP posture, both documented as caveats); or
the M8 docs plan diverging from the `/docs/` slot layout recorded here.
