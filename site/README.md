# site/ — the public marketing site (built, undeployed)

Six complete static pages introducing Irrevon, built per the redesign contract
(`.scratch/redesign/site-architecture.md` RD5, as adjudicated by
`.scratch/redesign/REDESIGN-BRIEF.md` ruling A7). **Deploy is gated and
human-only** — see
[../.github/workflows/site-deploy.yml](../.github/workflows/site-deploy.yml)
(dispatch-only; the full gate list is recorded in
[docs/review-queue.md](../docs/review-queue.md)). The site is a repo
artifact only: it never ships in the Python wheel (ADR-0018) and shares no build
with `web/`.

## The six pages (ruling A7 — quality over coverage; no public stubs)

| Route | Page |
|---|---|
| `/` | Home — problem, the recorded seed-777 artifact, three mechanisms, non-guarantees, bench no-results teaser, clone-and-make CTA |
| `/platform` | **Engine** (honest title per RD5 §3.2) — components, conceptual architecture, implemented-today strip, capability declaration, roadmap boundary |
| `/how-it-works` | Mechanism — re-synthesis failure, identity derivation, three-dimension state model, the recorded ambiguous case, the whole C1/C2/C3 table, prior art credited |
| `/benchmark` | IrrevonBench — DRAFT status banner, credibility controls, the full baseline ladder, the kill criterion verbatim, metrics glossary, research integrity |
| `/security` | Security & trust — trust boundary, data posture, supply-chain practice, explicit non-claims |
| `/docs` | Docs — real quickstart (clone + uv + Docker; no package-index install), links to canonical repo documents, honest status |

Use Cases, About/Company, Contact, and any demo-request page are **omitted, not
stubbed** (ruling A7; the Book-a-Demo tension is an open owner decision, RD5 §4).
Navigation lists only the six built pages.

## Truth discipline

- **Claims registry:** every key claim lives in
  [`src/data/claims.ts`](src/data/claims.ts) (claim, source, epistemic label,
  badge); pages cite by id via the `Source` component, and
  [`CLAIMS.md`](CLAIMS.md) is generated from the registry
  (`pnpm claims:md`; `--check` gates drift).
- **Three-badge system** (`Badge.astro`, required on claim-bearing sections):
  `RECORDED ARTIFACT` (the seed-777 demo; exact numbers only from
  `web/fixtures/canonical/demo-artifact.json`), `CONCEPTUAL` (diagrams),
  `PREREGISTERED METHODOLOGY — NO RESULTS YET` (everything IrrevonBench).
- **What cannot appear anywhere** (RD5 §2): pricing, customers, testimonials,
  SLAs, benchmark numbers, uncited numbers, `pip install`, "exactly-once" /
  "rollback" unqualified, fake forms, employer identifiers.

## Architecture

- Astro `7.0.9` (exact pin — the newest 7.x release older than the 7-day
  `minimumReleaseAge` policy on 2026-07-21; 7.1.x was < 7 days old), static
  output, `passthroughImageService` (no sharp, no build scripts).
- **Zero JS by default.** The only JavaScript on any page is the inline theme
  boot + toggle (~1 KB total); the budget test fails any page over 10 KB inline
  JS or any fetched script file.
- **Base-path ready:** internal links go through `src/lib/url.ts`
  (`import.meta.env.BASE_URL`); the deploy workflow passes `--site`/`--base`
  from `actions/configure-pages` outputs. The repository URL is
  deployment-provided (`SITE_REPO_URL` env or the local git remote — never
  committed; the build fails if unresolved).
- **Vendored identity, drift-checked:** `scripts/sync-tokens.mjs` copies the
  workbench Instrument Steel reference tokens (and generates a
  `prefers-color-scheme` block for no-JS dark mode); `scripts/sync-fonts.mjs`
  copies the self-hosted IBM Plex woff2 subsets. Both `--check` in `pnpm check`.
  Site-local additions (marketing display scale) live only in
  `src/styles/site.css`.
- One configurable project name (`src/config.ts` `SITE_NAME`) — set to "Irrevon"
  per ADR-0023; kept configurable by design.

## Dependency register (per-dep justification)

| Package | Why |
|---|---|
| `astro` 7.0.9 | The static site framework (zero-JS-by-default; Pages `site`/`base` support) |
| `@astrojs/check` 0.9.9 | `astro check` type/diagnostic gate |
| `typescript` 5.9.3 | Required by astro check; same pin as `web/` |
| `@playwright/test` 1.61.1 | a11y/link/budget gates + review screenshots; same pin as `web/` |
| `@axe-core/playwright` 4.12.1 | WCAG 2.2 AA scans as test failures; same pin as `web/` |

pnpm hardening matches `web/`: `allowBuilds` all-false, `minimumReleaseAge`
10080, `trustPolicy: no-downgrade`, `blockExoticSubdeps`, exact pins, frozen
lockfile in CI. One reviewed `trustPolicyExclude`: `chokidar@4.0.3` (19 months
old, canonical maintainer; attestation-artifact signal — see
pnpm-workspace.yaml).

## Commands

```bash
export ASTRO_TELEMETRY_DISABLED=1   # zero-telemetry posture applies to builds too
                       # (CI sets this in .github/workflows/site-deploy.yml)
pnpm install           # Node 24 (.nvmrc), pnpm 11
pnpm dev               # local dev
pnpm check             # astro check + token/font/claims drift
pnpm build             # static build to dist/
pnpm test              # Playwright: axe (both themes, all pages), keyboard,
                       # no-JS render, internal links, JS budget + zero external requests
pnpm shots             # 1440/768/375 × light/dark review screenshots -> shots/
node scripts/capture-workbench.mjs   # product imagery from a running web/ dev server
```

## Measured results (2026-07-21, this commit)

- Build: 6 pages, green. `astro check`: 0 errors / 0 warnings.
- Playwright: 24/24 checks green (12 axe runs = 6 pages × 2 themes, keyboard,
  no-JS, links, budgets).
- JS weight: **1,032 bytes inline per page, zero fetched scripts** (budget
  ≤ 10 KB; brief goal ≤ 5 KB — met with margin). CSS: one 14 KB file, ~3 KB
  gzip (≤ 40 KB budget).
- Claims registry: 49 claims, all source-mapped; CLAIMS.md generated + drift-gated.

## Notes for the integrator

1. **Deploy workflow:** DONE at consolidation (2026-07-21) — the artifact now
   lives at `.github/workflows/site-deploy.yml` (dispatch-only; deploy itself
   stays blocked behind the gates recorded in the review queue).
2. **Root touches made by this task:** one clearly-marked appended Makefile
   block (`site-check`, `site-build`, `site-test`); nothing else at root. No
   root `pnpm-workspace.yaml` exists (workspaces are per-directory) — none added.
3. **Review-queue appends** proposed by RD5 §7: appended at consolidation
   (2026-07-21) — see the review queue (marketing-site ADR item, ADR-0018
   Pages-slot amendment). Resolution remains human-only.
4. Workbench screenshots (`public/images/`) were captured from the running
   fixture-backed `web/` app at 1440×900 (2× DPR), both themes, SYNTHETIC
   FIXTURE banner deliberately in frame. Re-capture with
   `scripts/capture-workbench.mjs` after any workbench visual change
   (e.g. the Slice-7 h238/E1 cutover), then re-run `pnpm sync:tokens`.
