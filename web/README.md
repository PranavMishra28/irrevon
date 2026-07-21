# Irrevon Workbench (`web/`)

Local-first, single-user, **read-only** evidence workbench for Irrevon. Fixture-backed
(v0.1): all data comes from MSW-served, schema-derived fixtures; the browser never starts
an effect and no build of this app can mutate anything.

Contract: `.scratch/rc/frontend/BRIEF.md` (reconciled implementation brief — local-only
working material, never committed; the durable decisions live in
[ADR-0016](../docs/decisions/0016-frontend-workbench-stack.md) and this README).

Status: all six BRIEF slices are implemented against the implemented engine on `rc/v0.1`.
Types generate from the five admitted JSON Schemas plus the RFC-002 §3 canonical state
tables (`pnpm codegen`, committed, drift-gated, SHA-256-pinned in
`contracts/schema-pins.json`). The canonical fixtures are **captured transcripts of the
real engine** (`scripts/capture-fixtures.py`, seed 777; commit + derivations recorded in
`fixtures/canonical/provenance.json`): Q1/Q2 exchange envelopes, verbatim
`irrevon inspect --json` payloads (the flagship one from the real SIGKILL demo database),
the `irrevon doctor --json` transcript, the demo JSONL artifact, and the loaded capability
declaration — schema-validated at capture, drift-gated by `fixtures/manifest.sha256`.
Still honestly absent: benchmark run schemas (BI-7 → Bench keeps its no-runs state),
live mode (BI-4 → the read server is deferred to the `serve` workstream), and evidence
bundles beyond digests (redaction pipeline pending → digest-only by policy).

## Working on it

```sh
# toolchain: Node 24 LTS (.nvmrc) + pnpm 11 (corepack)
pnpm install --frozen-lockfile
pnpm dev            # Vite dev server (mock mode), http://localhost:5199
pnpm check          # typecheck + lint + stylelint + format + unit/story tests
pnpm e2e            # Playwright workflows + a11y against the built review app
pnpm vrt            # VRT — authoritative only inside the pinned Linux container
pnpm build:review   # fixture-backed review build (mock mode allowed)
pnpm build          # production build; refuses mock mode
```

Notes:

- **Data modes.** `mock` (MSW, permanent “SYNTHETIC FIXTURE” banner) is dev/test/review
  only; a production build with mock selected fails. Live mode is blocked on the ratified
  loopback read server (BI-4) and never falls back to fixtures.
- **Strangers never need Node.** This directory is contributor-tooling only; packaged
  builds ship as static assets served by the CLI (deferred until BI-4).
- **Zero telemetry.** No network requests leave loopback (E2E-enforced), fonts are
  self-hosted, Storybook telemetry is disabled.
- **Supply chain.** pnpm blocks all lifecycle scripts (`allowBuilds` all-false),
  enforces a 7-day release age, no provenance downgrades, no exotic subdeps; every
  dependency is exact-pinned.

## Dependency register

Every direct dependency is justified against the BRIEF's budget. Additions require a new
row here plus a size-limit delta in the PR.

### Runtime

| Package                  | Version  | Justification (BRIEF §5)                                                  |
| ------------------------ | -------- | ------------------------------------------------------------------------- |
| `react`, `react-dom`     | 19.2.7   | UI runtime                                                                |
| `@tanstack/react-router` | 1.170.18 | typed path + search params; file-based SPA routes                         |
| `@tanstack/react-query`  | 5.101.2  | server-state cache over the read-only Q1–Q3 contracts                     |
| `@tanstack/react-table`  | 8.21.3   | headless grid for effects/receipts/findings tables                        |
| `@base-ui/react`         | 1.6.0    | sole behavior-primitive library (dialogs, autocomplete palette, tooltips) |
| `lucide-react`           | 1.24.0   | single-weight icon set, consumed only via the internal registry           |

### Development / test only

| Package                                                                                                                                                                                     | Version               | Justification                                                                                                                                                                                                                                         |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `vite`, `@vitejs/plugin-react`, `@tailwindcss/vite`, `tailwindcss`                                                                                                                          | 8.1.4 / 6.0.3 / 4.3.2 | build + CSS-first token system                                                                                                                                                                                                                        |
| `@tanstack/router-plugin`                                                                                                                                                                   | 1.168.20              | file-based route generation (newest release passing the 7-day age gate)                                                                                                                                                                               |
| `typescript`                                                                                                                                                                                | 5.9.3                 | `[OQ: FE-PIN-1]` resolved: TS 7.0.2 typechecks the scaffold but typescript-eslint 8.64 crashes against it (`typescript-estree` shared.js `Cjs` read); pinned the newest stable 5.x line that the full toolchain passes, per the BRIEF's fallback rule |
| `typescript-eslint`, `eslint`, `eslint-plugin-jsx-a11y`, `eslint-plugin-boundaries`, `eslint-import-resolver-typescript`, `@tanstack/eslint-plugin-query`, `@tanstack/eslint-plugin-router` | see `package.json`    | F0 static gates: strict typed lint, a11y lint, import-boundary enforcement (resolver needed for TS-aware boundary resolution)                                                                                                                         |
| `stylelint`, `stylelint-declaration-strict-value`                                                                                                                                           | 16.26.1 / 1.11.1      | token-usage lint on color-bearing CSS longhands                                                                                                                                                                                                       |
| `prettier`                                                                                                                                                                                  | 3.9.5                 | formatting gate                                                                                                                                                                                                                                       |
| `vitest`, `@vitest/browser-playwright`                                                                                                                                                      | 4.1.10                | unit + browser-mode story tests                                                                                                                                                                                                                       |
| `storybook`, `@storybook/react-vite`, `@storybook/addon-a11y`, `@storybook/addon-vitest`                                                                                                    | 10.5.0                | component contract docs; axe-as-error story tests                                                                                                                                                                                                     |
| `@playwright/test`, `@axe-core/playwright`                                                                                                                                                  | 1.61.1 / 4.12.1       | E2E, a11y scans, VRT comparator                                                                                                                                                                                                                       |
| `msw`                                                                                                                                                                                       | 2.15.0                | the only mock transport (dev/test/review)                                                                                                                                                                                                             |
| `json-schema-to-typescript`                                                                                                                                                                 | 15.0.4                | schema → committed types codegen (waiting on post-integration schemas)                                                                                                                                                                                |
| `size-limit`, `@size-limit/preset-app`                                                                                                                                                      | 12.1.0                | bundle/performance budgets                                                                                                                                                                                                                            |
| `@ibm/plex-sans`, `@ibm/plex-mono`                                                                                                                                                          | 1.1.0 / 2.5.0         | font acquisition only; Latin1 WOFF2 subsets copied to `public/fonts` by `pnpm fonts:sync` (drift-checked)                                                                                                                                             |
| `@types/node`, `@types/react`, `@types/react-dom`                                                                                                                                           | see `package.json`    | type definitions                                                                                                                                                                                                                                      |

### Version-pin deviations from the BRIEF

The BRIEF's §5 pins were verified 2026-07-21; several had newer releases inside the 7-day
`minimumReleaseAge` window, so the newest _mature_ release was pinned instead (never a
downgrade below the BRIEF's verified line): `storybook` 10.5.0 (not 10.5.3),
`tailwindcss` 4.3.2 (not 4.3.3), `vite` 8.1.4 (not 8.1.5), `typescript-eslint` 8.64.0
(not 8.65.0), `@tanstack/eslint-plugin-query` 5.101.2. `semver@6.3.1` (transitive, via
Babel) is excluded from `trustPolicy` only — it predates npm provenance; see
`pnpm-workspace.yaml`.

## Budgets (enforced by `pnpm size`)

Redesign goals (REDESIGN-BRIEF A3): initial ≤115 KB internal cutover goal under the
published 120 KB soft target; lazy ≤250 KB; CSS ≤20 KB. Palette, shortcut help, the
mobile drawer, and every route body (including the causal graph, which only the detail
route chunk carries) are dynamic chunks; the Effects list never imports graph code
(E2E-enforced).

| Budget                                          | Target  | Hard gate | Current (2026-07-21, redesign) |
| ----------------------------------------------- | ------- | --------- | ------------------------------ |
| Initial route JS (gzip)                         | ≤120 KB | ≤180 KB   | ~89.7 KB                       |
| Total lazy JS (gzip, excl. dev-only MSW worker) | ≤250 KB | ≤350 KB   | ~208 KB                        |
| Total CSS (gzip)                                | ≤20 KB  | ≤50 KB    | ~8.6 KB                        |

## Redesign test suites (REDESIGN-BRIEF §7)

Beyond the original shell/investigation E2E: `overview.spec.ts`,
`attention.spec.ts`, `findings.spec.ts`, `graph.spec.ts` (keyboard order, URL
selection round-trips, timeline↔graph sync, no-fleet-graph guarantee),
`surfaces.spec.ts` (adapters/demo/health/bench), `responsive.spec.ts`
(320/375/768/1120/1440 reflow matrix + target sizes + reduced motion),
`read-only.spec.ts` (route-wide zero non-loopback and zero non-GET/HEAD
requests), and `live-boundary.spec.ts` (builds a real live artifact in-test and
proves a failed live read reveals no fixture, registers no worker, and that a
mock production build is refused). All Playwright projects run with zero
retries — a flake is a bug.

## VRT

Baselines live in `e2e/visual/__baselines__` and are Linux-only, generated inside the
pinned Playwright container:

```sh
docker run --rm --ipc=host -e CI=1 -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v1.61.1-noble \
  bash -lc 'corepack enable && \
            pnpm install --frozen-lockfile --store-dir /tmp/pnpm-store && \
            IRREVON_VRT_CONTAINER=1 pnpm exec playwright test --project=vrt'
```

Add `--update-snapshots` only when a PR states why pixels changed. A bare local `pnpm vrt`
outside the container skips the project by design.
