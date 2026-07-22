---
title: "Site hosting — deploy `site/` to Vercel at the origin root, retiring the GitHub Pages plan"
sourcePath: "docs/decisions/0027-site-vercel-deploy.md"
sourceSha256: "4c9bf0087e0202ee7a85199605ad24d8fe61ab2f90af37ce4dbec7fe3b02011a"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0027"
  status: "accepted (owner deploy directive, 2026-07-21)"
  date: "2026-07-21"
  supersedes: "ADR-0025 decision items 4–5 (gated Pages deploy mechanics + Pages slot layout); amends ADR-0018's GitHub-Pages-only hosting ruling for the site surface (its $0-recurring-cost and no-SaaS rulings stand)"
---

## Context

ADR-0025 landed the `site/` package with deploy gated behind a dispatch-only GitHub Pages
workflow; AM-21/AM-23 (review queue §1) proposed the shared-Pages-slot mechanics that
deploy would have required. The owner's written deploy directive of 2026-07-21 ordered the
site published on Vercel instead `[DD]`. Vercel's free Hobby tier serves static output at
$0 recurring cost `[VF: vercel.com/pricing, 2026-07]`, keeping ADR-0018's cost ruling
intact, and — unlike GitHub Pages — sets real response headers, which converts
`site/docs/headers-spec.md` from a future-edge spec into applied configuration.

## Decision

The public site deploys to Vercel as a static deployment of the built `site/dist` output,
served at the **origin root** (base `/` — the GitHub Pages `/<repo>/` project base path is
retired along with the `site-deploy.yml` workflow). [`site/vercel.json`](../../site/vercel.json)
is the applied form of the header spec: CSP `frame-ancestors 'none'`, HSTS, nosniff,
Referrer-Policy, Permissions-Policy, COOP, X-Frame-Options, and the cache rules
(`/_astro/*` immutable; everything else short-TTL). The per-page meta-CSP with
build-computed script hashes (`scripts/inject-csp.mjs`) continues to ship in the HTML.
The origin and repository URL remain deployment-provided (`SITE_ORIGIN` /
`VERCEL_PROJECT_PRODUCTION_URL`; `SITE_REPO_URL` / Vercel git metadata / local git
remote) — never committed. Deploys remain human-gated acts: an owner-directed production
build + upload, not a push-triggered pipeline.

## Alternatives

- **GitHub Pages (the ADR-0025 plan)** — no response headers (meta-CSP-only posture),
  project-site base path unless a custom domain lands, and the shared-slot mechanics
  AM-21/AM-23 had to paper over; retired by the owner's directive.
- **Cloudflare Pages / Netlify** — equivalent static hosts; no differentiator was
  evaluated to outweigh the owner's explicit platform choice `[DD]`.
- **Keeping both (Pages + Vercel)** — two live origins means split canonical URLs and a
  second deploy surface to keep honest; rejected.

## Consequences

- `.github/workflows/site-deploy.yml` is deleted; `docs/ci.md`, `site/README.md`, and the
  root README describe the Vercel deployment. AM-21/AM-23's Pages-slot mechanics are
  overtaken (recorded in the review queue — those rows stay as history, append-only).
- The site's own security page and `headers-spec.md` now describe applied headers, and
  `robots.txt` sits at the origin root, so it is authoritative (RFC 9309) `[VF]`.
- The M8 docs surface stays the site's `/docs/` section (AM-23's substance is unchanged;
  only the hosting slot moved).
- Conformance: `make site-check` / `site-build` / `site-test` gate the artifact; the
  live-deployment header set is verifiable with `curl -sI` against the production URL.

## Risks

- Vercel Hobby-tier terms or limits change — blast radius is a re-host of a fully static
  artifact (the site has no Vercel-specific runtime coupling; `vercel.json` transcribes
  the host-neutral header spec).
- The Vercel-provided `*.vercel.app` origin is temporary until the custom-domain purchase
  (owner spend decision, review queue §3 item 21); canonical/sitemap/OG URLs re-derive
  from the deploy-provided origin at the next build, but external links to the old origin
  would rot — mitigated by deciding the domain before wide publication.

## Reopen trigger

A custom domain purchase (re-derives the origin and makes the HSTS `preload` question
live); Vercel pricing/ToS changes touching the Hobby tier; or any need for the site to
carry server-side behavior (forbidden surface per ADR-0018 — would need its own ADR).
