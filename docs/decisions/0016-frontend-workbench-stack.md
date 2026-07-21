---
id: ADR-0016
title: Frontend workbench stack — Vite SPA + TanStack, schema-derived types, pnpm-hardened
status: accepted (ratified in writing by the owner, 2026-07-21)
date: 2026-07-21
supersedes: —
---

## Context

An owner directive (2026-07-21, amendment AM-15) authorizes a local-first developer
workbench UI for Detent: single-user, no auth, strictly read-only over the engine's
read-only query contracts (effects, findings, benchmark-run summaries — specified in
docs/rfc-002-engine-design.md §9), rendering evidence: lifecycle timelines, receipts,
findings with resolutions, benchmark summaries. Constraints inherited from the repo: the UI
can never reach gate/dispatch/resolve (master doc §6.3 trust boundary; resolution is
deliberately omitted from the query surface); zero telemetry; the <30-minute stranger test
(master doc §10) is already budgeted by the CLI bootstrap, so the workbench may add no
required steps — strangers never need Node; assets ship prebuilt with the CLI. The frontend
is TypeScript regardless of ADR-0013: it consumes language-neutral JSON contracts, not
backend objects. ADR-0013's TypeScript rejection cited npm's worm-class supply-chain
campaigns (CISA 2025-09-23); the frontend cannot avoid npm and must therefore confine it
(dev-time only) and mitigate it mechanically. Static-serve-from-CLI is the verified pattern
of the closest comparable tools (Temporal UI assets embedded in ui-server; Airflow 3 React
UI served by the FastAPI api-server; Prefect UI served by `create_ui_app`); Vite's own docs
disclaim `vite preview` as a production server.

**Sequencing note (recorded, per policy):** the independent simplification review (C2,
2026-07-21) recommended deferring the workbench until after M8. The owner's written
directive of 2026-07-21 **overrules that deferral**: frontend work proceeds now, on its own
branch (`web/` arrives via the frontend workstream), subject to every constraint above. The
review's substantive cut — the two-band diff exhibit and other polish — stays deferred; the
first-slice evidence surface remains `detent inspect` plus a field table.

## Decision

Build the workbench as a **focused Vite single-page app** (Vite 8, Rolldown) in **`web/`**
at the repo root, shipped as static assets served locally by the `detent` CLI (the local
read-only endpoint is un-deferred by AM-15; routes = query contracts + static assets + SPA
history fallback; loopback-only; zero mutation routes). Stack, one line per layer:

- **Runtime/PM:** Node 24 LTS (pinned), pnpm 11 with lifecycle scripts blocked
  (`allowBuilds: []`), `minimumReleaseAge` 10080 (7 days), `trustPolicy: no-downgrade`,
  `blockExoticSubdeps: true`, committed lockfile, `--frozen-lockfile` CI, exact-pinned
  direct deps, a direct-dependency budget with per-dep justification.
- **Framework/routing:** React + **TanStack Router** (typed path params for
  `effect_id`/`finding_id`/`run_id` routes; schema-validated typed search params carrying
  query filters and cursors so every evidence view is a shareable URL). No SSR: loopback
  serving, no SEO, no auth, no personalized first paint.
- **Data:** **TanStack Query v5** (polling via `refetchInterval`; `useInfiniteQuery` over
  the cursor envelope). Types generated from the repo's JSON Schemas by
  **json-schema-to-typescript** (schema → TS, matching the repo's direction of authority;
  generated output committed, CI fails on regeneration drift). No runtime validator in the
  app path (loopback trust domain; `schema_version` checked at the fetch wrapper); schema
  validation enforced at the fixture boundary by the existing `check-jsonschema` gate
  pattern. Until the deferred record schemas are admitted (ADR-0019), codegen targets a
  vendored copy of their proposal text, clearly marked, swapped at admission.
- **Mock mode/fixtures:** **MSW 2** as the single mock layer (dev browser, Vitest,
  Storybook, Playwright). Fixtures are standalone JSON files shaped as the query contracts,
  schema-validated in CI, typed via `satisfies` at the handler import, resolved by scenario
  name — never hardcoded into components; replaceable by demo-seed-derived captures once
  the engine exists.
- **Client state beyond Query:** none. URL state lives in typed search params; ephemeral
  state in local component state. Zustand only against a recorded trigger (cross-cutting
  client-only state needed by ≥3 unrelated components, not derivable from URL/server state).
- **Tables:** TanStack Table **v8** (v9 is beta — not adopted). TanStack Virtual deferred
  behind a measured threshold (>1,000 mounted rows by design AND INP >200 ms); below that,
  cursor pagination is the fix.
- **Graphs:** none. Every first-slice view is a linear sequence, table, or fixed diagram —
  a hand-rolled static SVG timeline, not React Flow. React Flow only if a genuinely
  interactive multi-effect graph view is added.
- **Animation:** CSS transitions + View Transitions API, honoring
  `prefers-reduced-motion`; Motion deferred. **Command palette:** deferred; cmdk when added.
- **Quality gates:** Storybook 10 (CSF factories, a11y addon, vitest addon) with stories as
  the component-test corpus; Vitest 4 browser mode (Playwright provider) + node mode for
  pure logic; Playwright E2E over the built assets with local, in-repo visual baselines
  pinned to one CI environment; axe-core enforced per story and per E2E flow; ESLint 10
  flat config + typescript-eslint strictTypeChecked + jsx-a11y; Prettier.
- **Integration:** Make remains the single entry point (`web-setup`, `web-codegen`,
  `web-dev`, `web-check`, `web-test`, `web-e2e`, `web-build`); `make check` runs
  `web-check` when `web/` exists; CI jobs are path-filtered on `web/**`, layered,
  SHA-pinned actions, no secrets in any frontend job.

## Alternatives

- **Next.js** — SSR/RSC machinery and a server runtime a local-first, loopback, no-auth
  workbench cannot use; largest dependency and upgrade surface; static-export mode fights
  its defaults.
- **TanStack Start** — same router plus an SSR/server-function layer whose "server" role is
  already taken by the `detent` CLI.
- **React Router 7** — untyped search params in SPA mode forfeit the typed-URL-state
  property the evidence views are built on.
- **TypeBox / zod codegen** — both invert or blur the direction of authority (JSON Schema
  files are the canonical, ADR-gated trust boundary); zod adds a runtime validator with
  imperfect 2020-12 semantics.
- **Fixture server instead of MSW** — a second process to run and drift.
- **Biome instead of ESLint+Prettier** — attractive single-binary posture, but type-aware
  and a11y rule coverage is currently partial vs typescript-eslint strict (see Reopen).
- **npm as package manager** — no default script-blocking, release-age delay, or
  exotic-source blocking; strictly weaker against the documented attack class.
- **apps/web + JS workspace tooling** — implies a multi-app JS monorepo; there is one app
  and the task runner is Make.

## Consequences

Easier: a single static build artifact the CLI serves; typed URLs make every filtered
evidence view shareable; schema-derived types + fixture validation make frontend/contract
drift a CI failure in the same commit that changes a schema; stories triple as docs, visual
review, and tests; strangers remain Node-free. Harder: a second toolchain (Node/pnpm)
exists for contributors and CI; codegen adds a build step; polling bounds freshness at the
poll interval. Conformance: CI codegen-drift check (types ≡ schemas); fixture
schema-validation gate; the read-only property is structural (no mutation routes) and E2E
asserts no workbench interaction issues a mutating request in mock mode.

## Risks

npm supply chain remains the dominant risk even confined to dev-time: CVE-2026-45321
(TanStack namespace compromise, 2026-05) proved valid provenance can attest to malware.
Blast radius: a contributor/CI machine at build time, never a stranger's machine or the
engine runtime; the mitigations above (script-blocking, 7-day release age, lockfile-only
CI, exotic-source blocking, dep budget) would have neutralized that incident. CSF factories
are Preview (React-only). TanStack Table v9 will eventually force a major migration.
Solo-maintainer cost of a second stack — bounded by the minimal-deps budget and deferred
per-need libraries.

## Reopen trigger

Any of: (a) the workbench needs SSR or server-only code paths; (b) a view crosses the
virtualization threshold; (c) a genuinely interactive multi-effect graph view is added;
(d) Biome reaches typed-lint + a11y parity with typescript-eslint strict; (e) a
supply-chain incident touches any pinned direct dependency — immediate audit; (f) TanStack
Router or Query goes unmaintained >6 months; (g) Node 24 exits Active LTS (2026-10) —
scheduled bump to Node 26 LTS.
