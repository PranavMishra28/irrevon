# T-113: Harden site accessibility semantics

---
id: T-113
status: done
depends_on: []
invariant: "ADR-0025 truth discipline and zero-JS-by-default site contract remain unchanged"
---

## Objective

Correct four verified, low-risk accessibility concerns in the marketing site without
changing its design, claims, dependencies, or deployment surface.

## Why

The public discovery surface is required to pass its accessibility and keyboard gates
under ADR-0025 `[DD]`. A source-citation component currently sits inside a paragraph on
Home even though the component renders its own paragraph `[VF]`; the skip-link target is
not explicitly focusable `[VF]`; and critical controls have no deliberate forced-colors
treatment `[VF]`. The self-hosted fonts already use non-blocking `font-display: swap`
`[VF]`, so that item requires a regression guard rather than a source change.

## Context — read these first

- `AGENTS.md`
- `site/README.md`
- `docs/decisions/0016-frontend-workbench-stack.md`
- `docs/decisions/0025-site-discovery-surface.md`
- `docs/decisions/0027-site-vercel-deploy.md`
- `site/e2e/`
- `site/src/components/Source.astro`
- `site/src/layouts/Base.astro`
- `site/src/pages/index.astro`
- `site/src/styles/site.css`

## Scope

**Allowed to write:** `tasks/T-113-harden-site-accessibility-semantics.md`,
`site/src/pages/index.astro`, `site/src/layouts/Base.astro`,
`site/src/styles/site.css`, `site/e2e/a11y.spec.ts`.

**Forbidden:** every other path; dependency changes; analytics or tracking changes;
feedback widgets; imagery; claim, product-scope, benchmark, scientific, or marketing-copy
changes; deployment or repository-state changes; workbench changes.

## Acceptance criteria

- [x] Home renders the claim source under `.hero-proof-src` without invalid nested
      paragraph markup, and a focused regression test proves the wrapper/component shape.
- [x] Activating the first-tab-stop skip link moves focus to the explicitly focusable
      `main#main` target, and the skip link has a visible keyboard focus treatment.
- [x] Every site `@font-face` declaration remains non-blocking with
      `font-display: swap`; `font-display: block` is absent and regression-tested.
- [x] Under `forced-colors: active`, critical link/button/input/summary controls retain
      system-color borders and keyboard focus, with the active primary/step control
      distinguishable.
- [x] Node 24 `make site-check`, `make site-build`, and `make site-test` exit 0.
- [x] `make check` and `git diff --check` exit 0.

## Required validation

```bash
node --version
make site-check
make site-build
make site-test
make check
git diff --check
```

Run `make site-vrt` only if the documented container-only mechanism is locally available;
otherwise record that manual visual/assistive-technology review remains outside this
automated pass.

## Documentation updates

This task record only. The site README's architecture and command documentation do not
change.

## Human review triggers — stop and ask if:

- A fix needs JavaScript, a dependency, a design-system change, new product copy, or a
  deployment/configuration change.
- A defect is not present and addressing it would require inventing behavior.
- Validation exposes a failure outside the allowed paths.

## Definition of done

All criteria are checked; validation output is recorded below; no file outside the allowed
scope is written; status is `done`.

## Validation evidence

- Node `v24.18.0` (`arm64`).
- `make site-check`: exit 0; Astro reported 0 errors and 0 warnings, and every
  drift gate matched.
- `make site-build`: exit 0; 58 pages built, Pagefind indexed 43 pages, and CSP
  hashes were injected into all 58 HTML pages.
- `make site-test`: exit 0; 321 Playwright checks passed with zero retries,
  including all-page dual-theme axe checks and the new semantics, focus,
  font-display, and forced-colors regressions.
- Focused accessibility rerun: 6 passed.
- `make check`: exit 0; links, schemas, secret scans, frozen/integrity checks,
  asset/notice registries, and benchmark integrity all passed.
- `git diff --check`: exit 0.
- No `site-vrt` target or container-backed marketing-site pixel comparator is
  documented. `pnpm shots` is a screenshot-review command rather than VRT, so it
  was not represented as a visual-regression gate.
- Manual Windows High Contrast, VoiceOver, and NVDA review remain human testing
  limitations; this pass covers Chromium forced-colors emulation and automated
  keyboard/axe checks.
