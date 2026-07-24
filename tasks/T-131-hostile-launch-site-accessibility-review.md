# T-131: Audit the integrated launch site as a skeptical evaluator

---
id: T-131
status: done
depends_on: [T-128, T-129]
invariant: "master doc §6–§9 product scope, benchmark boundaries, and security claims remain truthful"
---

## Objective
Independently identify substantiated launch-site truth, adoption, accessibility, and
provenance defects without changing implementation.

## Why
The integrated public surface needs a final adversarial read from both open-source
maintainer and enterprise-evaluator perspectives before the owner makes any publication
decision.

## Context — read these first
- `AGENTS.md`
- `docs/project-status.md`
- `docs/execution-plan.md`
- `site/README.md`
- `site/src/layouts/Base.astro`
- `site/src/pages/`
- `site/src/content/guides/`
- `site/e2e/`

## Scope
**Allowed to write:** this task file only.

**Forbidden:** all implementation, generated artifacts, repository settings, release or
deployment actions, publication, commits, and any file not explicitly allowed above.

## Acceptance criteria
- [x] Representative 1440/1024/768/390/320 light/dark screenshots plus forced-color and
      reduced-motion evidence are inspected.
- [x] Ordinary-page jargon, navigation/footer focus, community truth, source quickstart
      ordering, evidence links, provenance/smoke coverage, and publication/install truth
      are reviewed.
- [x] Focused static or browser checks are run where useful.
- [x] Findings include exact file/line evidence and the smallest safe fix.
- [x] No implementation file is changed.

## Required validation
- Read-only source and built-output inspection.
- Focused browser/static checks where they materially test the requested contracts.
- `git diff --check`.

## Documentation updates
This task file only.

## Human review triggers — stop and ask if:
- Verification would require changing implementation, external settings, deployment,
  publishing, secrets, or repository history.

## Definition of done
The audit is complete; only substantiated findings are reported; no implementation file
is changed; task status is `done`.

## Independent findings

### P1 — The home-page quickstart cannot complete the current bootstrap contract

`site/src/pages/index.astro:282-287` omits the generated `.env.example` copy/export
and the required second `irrevon init` after Postgres starts. Its first `init` comment
also says "then migrations" even though `src/irrevon/cli/init_cmd.py:97-107` refuses
to attempt migrations without `IRREVON_MIGRATION_DSN`. The canonical source flow is
correct at `README.md:42-54`, `site/src/content/guides/getting-started.md:29-39`,
and `site/src/pages/install.astro:48-58`. The claim behind the broken snippet also
compresses away those required steps at `site/src/data/claims.ts:340-344`.

Smallest safe fix: make the home snippet mechanically match the tested canonical
source flow (including `cp`, export, database start, and second `init`), update the
claim text, and add a drift test that compares the public snippets to one canonical
sequence.

### P1 — The production smoke check proves syntax, not intended deployment identity

`scripts/site-production-smoke.py:37-88` accepts any nonzero 40-character SHA and
only checks that eight label strings occur somewhere in `index.html`.
`tests/scripts/test_site_production_smoke.py:16-54` consequently has no negative
coverage for a wrong-but-valid SHA, wrong canonical origin, stale footer/nav,
missing sitemap/robots/assets, or a weakened/absent `site/vercel.json` security and
cache policy. `Makefile:243-244` supplies no expected SHA or origin.

The current artifact demonstrates the gap: `site/dist/index.html` and its sitemap
use `https://irrevon.example/`, yet the smoke command reports success. This is not
a claim about a deployed site; it is evidence that the release check would accept
the wrong canonical origin. Likewise, a different valid full SHA would pass.

Smallest safe fix: require `--expect-commit` and `--expect-origin`; compare the
manifest and footer commit to that SHA; check canonical/OG/sitemap/robots against
the exact origin; require launch assets; reject the old `Engine`/`Research` nav and
`Repository`/`Policies` footer; and validate the committed header/cache policy.
Add one negative test per contract.

### P1 human gate — Community destinations are advertised while Discussions is disabled

`README.md:251-260` and `SUPPORT.md:14-16` expose clickable Discussion-category
destinations, while `SUPPORT.md:22-27` says Discussions is disabled and those
destinations "must not be represented as available." The issue chooser also exposes
the same disabled destinations at `.github/ISSUE_TEMPLATE/config.yml:6-14`.
Meanwhile the primary `Community` navigation item
(`site/src/layouts/Base.astro:38-46`) lands on a contribution-only page
(`site/src/pages/contributing.astro:12-32`), not a community/status surface.

Smallest safe resolution: either complete the documented human enable/create/read-back
gate before merge, or withhold all clickable Discussion destinations while disabled
and label the navigation target `Contribute`. Do not present a dead category as an
available support path.

### P2 — Evidence links are not claim-specific

`site/src/components/Source.astro:13-29` receives the exact claim IDs but discards
them when building the URL: every "Technical provenance" link targets the top of
`site/CLAIMS.md`. A skeptical evaluator clicking two different claims therefore
lands at the same 54-row table without the selected claim identified.

Smallest safe fix: generate stable claim anchors and link the current claim ID as
a fragment (or link directly to the claim's commit-pinned source section). Add a
browser assertion that two distinct evidence links resolve to their distinct claim
records.

### P2 — Ordinary launch pages still expose unexplained internal codes

The home page uses `S-REF`, `B5`, `C1`, `C2`, and `C3` in ordinary marketing copy
at `site/src/pages/index.astro:44,80,100,178,186,254-256`; the beginner guide uses
`B5`, `C2`, and `Stage-B` at
`site/src/content/guides/getting-started.md:63-67`. Similar freeze codes appear on
the ordinary roadmap at `site/src/pages/roadmap.astro:61-64`. The surrounding copy
sometimes describes the concept but does not expand the identifier when first used.

Smallest safe fix: use plain-language names on launch and beginner pages
(`synthetic reference destination`, `durable-runtime comparison`,
`idempotency-keyed/queryable/opaque destination`, `design/operational freeze`).
Retain compact IDs only in specialized benchmark/adapter material, defining each
at first use.

### P3 — The primary navigation is visually overfull at phone widths

The eight persistent items in `site/src/layouts/Base.astro:38-46,190-208`, combined
with the unconditional wrapping rules at `site/src/layouts/Base.astro:416-440`,
produce a multi-row navigation plus a separate theme-control row at 390 and 320
pixels. There is no overflow and all targets remain keyboard-reachable, but the
header consumes a disproportionate share of the first viewport.

Smallest safe fix: preserve the same destinations behind one accessible compact
menu below a narrow breakpoint, or reduce the persistent phone-width set and expose
the remaining destinations from that menu. This is polish, not an accessibility
failure.

## Passing evidence

- All inspected 1440, 1024, 768, 390, and 320 light/dark screenshots are legible,
  coherent, and free of viewport-level overflow. The compact footer remains focused
  and truthfully says open source, local-first, and no scientific results.
- Forced-colors evidence retains borders, links, state, and focus. Reduced-motion
  evidence is static and the automated check finds zero active nonzero-duration
  animations.
- Publication wording is honest: `README.md:20-26` and
  `site/src/pages/install.astro:21-33,69-101` clearly state that no package-index
  release exists and render future install commands as planned/gated.
- `/version.json` has a strict six-field shape and production builds require a full
  SHA (`site/src/pages/version.json.ts:12-35`,
  `site/astro.config.mjs:38-56`). The finding above concerns comparison to the
  intended release identity, not the manifest's basic shape.

## Validation run

- Inspected the existing 1440/1024/768/390/320 light/dark screenshots plus
  `home-forced-colors.png` and reduced-motion demo beats.
- `pnpm exec playwright test --project=checks e2e/a11y.spec.ts e2e/links.spec.ts e2e/provenance.spec.ts e2e/install.spec.ts`
  — 154 passed.
- `python3 scripts/site-production-smoke.py --dist site/dist --expect-environment production`
  — passed, intentionally demonstrating the missing expected-origin check.
- `uv run pytest -q tests/scripts/test_site_production_smoke.py tests/scripts/test_site_integration_guide.py`
  — 5 passed.
- `git diff --check` — passed.
