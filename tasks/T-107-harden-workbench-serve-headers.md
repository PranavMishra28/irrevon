# T-107: Harden the packaged workbench response boundary

---
id: T-107
status: done
depends_on: []
invariant: "master doc §9 and RFC-002 §9: the browser surface is loopback-only and strictly read-only"
---

## Objective
Serve the packaged workbench with a restrictive, executable Content Security Policy and
defense-in-depth browser security headers without adding requests, dependencies, or write
capability.

## Why
ADR-0024 makes `irrevon serve` the loopback-only, read-only workbench boundary and ADR-0016
requires a self-contained static artifact with zero telemetry. The existing CSP did not
authorize the built pre-paint inline preference script, so browsers could block persisted
theme and density before application startup.

## Context — read these first
- `docs/master-doc.md` §9 and §12
- `docs/rfc-002-engine-design.md` §9 and §12
- `docs/decisions/0016-frontend-workbench-stack.md`
- `docs/decisions/0024-serve-read-surface.md`
- `web/README.md`
- `src/irrevon/serve.py`
- `tests/serve/test_static.py`

## Scope
**Allowed to write:** `tasks/T-107-harden-workbench-serve-headers.md`,
`src/irrevon/serve.py`, `tests/serve/test_static.py`,
`web/e2e/live-real/real-serve.spec.ts`, and `web/README.md`.

**Forbidden:** `docs/master-doc.md`, schemas, migrations, accepted ADR text, API payload
shapes, database privileges, bind configuration, product scope, dependencies, telemetry,
analytics/privacy policy, generated workbench assets, and VRT baselines. Anything not
listed as allowed is out of scope.

## Acceptance criteria
- [x] `uv run pytest tests/serve/test_static.py -p no:cacheprovider` exits 0 and proves
      HTML, static assets, API errors, and the missing-assets response carry the intended
      security headers.
- [x] The CSP returned for an HTML artifact contains `base-uri 'none'`, `object-src
      'none'`, `frame-ancestors 'none'`, and `form-action 'none'`; it contains no
      `unsafe-inline` in `script-src`.
- [x] Given an HTML artifact with a pre-paint inline script, the response CSP authorizes
      the SHA-256 of the exact script bytes and does not authorize a one-byte mutation.
- [x] The real packaged-workbench journey runs under its response CSP, preserves a chosen
      theme across reload, and makes no non-loopback request.
- [x] `make check` passes.

## Required validation
```sh
uv run pytest tests/serve/test_static.py -p no:cacheprovider
make py-test-serve
make web-e2e-live
make check
```

## Documentation updates
Update `web/README.md` to describe the response-header boundary and the CSP hash treatment
for the pre-paint script.

## Human review triggers — stop and ask if:
- Compatibility requires weakening `script-src`, adding an external origin/request, or
  changing the loopback/read-only contract.
- Validation exposes a need for a dependency, schema, migration, or accepted-ADR change.

## Definition of done
All criteria checked; validation output attached; documentation updates made; no writes
outside allowed scope; status set.

## Completion record — 2026-07-23
- `uv run pytest tests/serve/test_static.py -p no:cacheprovider` — 13 passed.
- `make py-test-serve` — 58 passed.
- `make web-e2e-live` — 5 passed, including the exact built-script hash, browser CSP
  violation listener, persisted pre-paint theme, and zero non-loopback request assertions.
- `pnpm typecheck && pnpm lint && pnpm format:check` — all passed.
- `make check` — all validation gates passed.
