# headers-spec.md — response headers for a future edge

Site operational material (not `docs/` — this is the site package's artifact).

**Why this file exists.** GitHub Pages serves static files and cannot set custom
response headers — no real CSP, no HSTS, no frame-ancestors, no nosniff. What ships
today is the subset a `<meta>` tag can carry (a per-page CSP with build-computed
script hashes — `scripts/inject-csp.mjs` — and a referrer policy), plus this spec: the
full header set to apply **verbatim** at whatever edge or host exists later, so
applying them is transcription, not design. Meta-CSP cannot carry `frame-ancestors`,
`report-uri`, or `sandbox` (CSP spec) — those wait here.

## The set

| Header | Value | Rationale |
|---|---|---|
| `Content-Security-Policy` | the built pages' meta policy + `; frame-ancestors 'none'` | Same computed-hash policy, plus the one directive meta cannot carry. Add `report-to` only when a collector is sanctioned (zero-telemetry posture is binding today). |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | TLS always. **`preload` deliberately omitted** — preload is near-irreversible (removal takes months and browser-list round-trips); adding it is a separate, flagged decision. |
| `X-Content-Type-Options` | `nosniff` | No MIME sniffing; the site serves exact types. |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Matches the shipped meta tag; full URL never leaks cross-origin. |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), interest-cohort=()` | The site uses none of these; deny by default. |
| `Cross-Origin-Opener-Policy` | `same-origin` | Severs window references from cross-origin openers. |
| `X-Frame-Options` | `DENY` | Legacy agent belt-and-braces for `frame-ancestors 'none'`. |

## Accepted risks / notes

- `style-src 'unsafe-inline'` is required by Astro's scoped-style inlining and a few
  style attributes; CSS injection on a static, no-input site is a negligible surface.
  Recorded as accepted, revisit if the site ever takes user input.
- Docs pages carry `script-src 'self' 'wasm-unsafe-eval'` for the self-hosted
  Pagefind bundle (WASM instantiation); every other page's script-src is hashes only.
- No `Cache-Control` prescription here: Pages controls caching today; set
  `max-age=600, stale-while-revalidate` for HTML and immutable for `/_astro/*` when
  an edge exists.
- These headers apply only when a fronting CDN or different host exists — both are
  currently rejected surfaces ($0 / no-accounts posture, ADR-0018). Until then, this
  file plus the meta subset is the honest maximum.
