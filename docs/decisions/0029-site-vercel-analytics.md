---
id: ADR-0029
title: Site telemetry — first-party Vercel Web Analytics + Speed Insights (amends the site's zero-telemetry posture)
status: accepted (owner platform directive, 2026-07-21)
date: 2026-07-21
supersedes: — (amends ADR-0025's site posture: the zero-fetched-scripts budget lane and the site half of the zero-telemetry claim; engine and workbench zero-telemetry are untouched)
---

## Context

The site shipped with a binding zero-telemetry posture: no analytics, zero fetched
scripts outside the docs search lane, enforced by the budget E2E lanes and asserted by
the claims registry (`zero-telemetry`) and the footer. On 2026-07-21 the owner directed
that the site "use the most capabilities of Vercel, like web analytics" with everything
enabled on the platform side `[DD]`. Vercel Web Analytics and Speed Insights are
cookieless, first-party measurements served and beaconed on the site's own origin
(`/_vercel/insights/*`, `/_vercel/speed-insights/*`) `[VF: vercel.com/docs/analytics]` —
the least-invasive form the directive can take.

## Decision

Every page loads the two static-HTML Vercel snippets (the `window.va`/`window.si`
bootstraps plus the deferred same-origin loaders `/_vercel/insights/script.js` and
`/_vercel/speed-insights/script.js`) from the shared layout. The truth surfaces change
with it, honestly: the budget E2E lanes now allow **exactly those two same-origin
loaders** and nothing else (external requests remain forbidden on every page); the
per-page CSP's `script-src` gains `'self'` (a static header cannot hash a
platform-served script; inline scripts still require build-computed hashes); the beacons
ride the existing `connect-src 'self'`; the claims registry, `/security` page, footer,
and `site/docs/headers-spec.md` state the new posture. Engine and workbench telemetry
posture is unchanged: zero, E2E-enforced.

Other platform capabilities were reviewed and deliberately not adopted: skew protection
(meaningless for a fully static site), Vercel image optimization (ADR-0025 chose
`passthroughImageService` + pre-optimized assets), deployment protection (a public
marketing site), and functions/ISR (server-side behavior is a forbidden surface per
ADR-0027's reopen trigger).

## Alternatives

- **Keep zero-telemetry** — overruled by the owner's directive.
- **`@vercel/analytics` / `@vercel/speed-insights` npm packages with `inject()`** — adds
  two dependencies and build coupling for what two script tags do on a static site; the
  packages target framework runtimes.
- **Third-party analytics (GA et al.)** — cookies, cross-site requests, consent surface;
  strictly worse than the platform's first-party option and contrary to the site's
  no-third-party-request discipline, which this ADR keeps.

## Consequences

- The budget lanes' contract changes from "zero fetched scripts" to "no fetched scripts
  except the two same-origin Vercel telemetry loaders" — a spec change under an owner
  directive, recorded here; the lanes are otherwise un-weakened (external requests still
  fail the gate, inline budget unchanged).
- `script-src 'self'` on all pages means any same-origin script file is loadable by the
  CSP; on a fully static origin new script files require a deploy, and the JS-creep
  drift gate (computed hashes for inline scripts) still holds.
- Analytics data appears in the Vercel dashboard only when the project-level toggles are
  enabled — a dashboard, owner-only act (the owner reports them enabled).
- Locally and in CI the loaders 404 harmlessly (the routes exist only on Vercel);
  nothing beacons from test runs.

## Risks

Vercel could change the endpoints' pathing or the Hobby tier's analytics terms — blast
radius is two script tags and the budget-lane allowlist. The measurement itself is
Vercel-hosted: the site's "nothing leaves the page" claim is now scoped to third parties,
which the updated claims text states plainly.

## Reopen trigger

Vercel moves the telemetry endpoints off the first-party origin (would violate the
same-origin-only rule and the CSP); the owner orders telemetry rolled back; or a
privacy/consent requirement (e.g. a jurisdictional ruling on cookieless analytics)
contradicts the "no consent surface needed" premise.
