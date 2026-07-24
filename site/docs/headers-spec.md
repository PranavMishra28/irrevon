# headers-spec.md — response headers, applied at the Vercel edge

Site operational material (not `docs/` — this is the site package's artifact).

**Why this file exists.** The site deploys to Vercel (ADR-0027), which serves real
response headers from the repository-root
[`vercel.json`](../../vercel.json) — that file is the applied form
of this spec; keep the two in sync (this file carries the rationale JSON cannot). The
per-page CSP still ships as a `<meta>` tag with build-computed script hashes
(`scripts/inject-csp.mjs`) because a static header cannot carry per-page hashes; the
response-header CSP adds `frame-ancestors` — the one directive meta-CSP cannot carry
(CSP spec; likewise `report-uri` and `sandbox`, both unused).

## The set

| Header | Value | Rationale |
|---|---|---|
| `Content-Security-Policy` | `frame-ancestors 'none'` (header) + the per-page meta policy with computed hashes | Both policies enforce: the header carries the directive meta cannot; the meta carries the per-page script hashes a static header cannot. The meta policy's `script-src` includes `'self'` for the same-origin Vercel telemetry loaders (`/_vercel/…/script.js`, ADR-0029 — platform-served, unhashable at build); their beacons ride `connect-src 'self'`. CSP `report-to` remains unset (Vercel Web Analytics/Speed Insights is the only sanctioned collector; a CSP violation collector would be a separate decision). |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | TLS always. **`preload` deliberately omitted** — preload is near-irreversible (removal takes months and browser-list round-trips); adding it is a separate, flagged decision. |
| `X-Content-Type-Options` | `nosniff` | No MIME sniffing; the site serves exact types. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Matches the shipped meta tag; full URL never leaks cross-origin. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), interest-cohort=()` | The site uses none of these; deny by default. |
| `Cross-Origin-Opener-Policy` | `same-origin` | Severs window references from cross-origin openers. |
| `X-Frame-Options` | `DENY` | Legacy agent belt-and-braces for `frame-ancestors 'none'`. |
| `Cache-Control` | `public, max-age=600, stale-while-revalidate=86400` everywhere; `public, max-age=31536000, immutable` for `/_astro/*`; `public, max-age=0, must-revalidate` for `/version.json` | Only `/_astro/*` assets are content-hashed. The provenance manifest must revalidate so it cannot conceal a stale deployment. Everything else keeps a short TTL. |
| `Content-Type` + `X-Robots-Tag` on `/version.json` | `application/json; charset=utf-8`; `noindex` | The machine-readable provenance endpoint is typed explicitly and is not a search destination. |

## Accepted risks / notes

- The owner-run production smoke receives the intended full commit SHA and
  canonical HTTPS origin explicitly. It checks this applied header configuration,
  including the no-cache `/version.json` rule, alongside built canonical/OG,
  sitemap, robots, asset, and provenance contracts before any upload.
- `style-src 'unsafe-inline'` is required by Astro's scoped-style inlining and a few
  style attributes; CSS injection on a static, no-input site is a negligible surface.
  Recorded as accepted, revisit if the site ever takes user input.
- Every page's `script-src` is `'self'` + per-page computed hashes (`'self'` covers the
  same-origin Vercel telemetry loaders and the Pagefind bundle; inline scripts still
  require hashes — `'self'` never permits inline). Docs pages add `'wasm-unsafe-eval'`
  for Pagefind's WASM instantiation.
- The deployed origin is the Vercel-provided production URL until a custom domain is
  purchased (an owner spend decision on the launch checklist, review-queue §3 item 21);
  `robots.txt` sits at the origin root and is authoritative (RFC 9309).
