# Detent Workbench (`web/`)

Local-first, single-user, **read-only** evidence workbench for Detent. Fixture-backed
(v0.1): all data comes from MSW-served, schema-derived fixtures; the browser never starts
an effect and no build of this app can mutate anything.

Contract: `.scratch/rc/frontend/BRIEF.md` (reconciled implementation brief).

Status: shell, tokens, palette, keyboard contract, Learn pages, and the status taxonomy
are implemented. Types and enums generate from the post-integration contracts on
`rc/v0.1`: the two ratified JSON Schemas plus the RFC-002 §3 canonical state tables /
§2.2 DDL closed sets (`pnpm codegen`, committed output, drift-gated, source hashes pinned
in `contracts/schema-pins.json`). Every surface that needs the EffectRecord /
DispatchReceipt / ReconciliationFinding / Q-envelope / demo-artifact / health schemas
renders an honest contract-pending state: ADR-0019 defers those record schemas to the M3
admission ADR, and this app does not invent parallel contracts.

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
| `lucide-react`           | 1.0.1    | single-weight icon set, consumed only via the internal registry           |

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

| Budget                                          | Target  | Hard gate | Current |
| ----------------------------------------------- | ------- | --------- | ------- |
| Initial route JS (gzip)                         | ≤120 KB | ≤180 KB   | ~132 KB |
| Total lazy JS (gzip, excl. dev-only MSW worker) | —       | ≤350 KB   | ~141 KB |
| Total CSS (gzip)                                | —       | ≤50 KB    | ~5.5 KB |

## VRT

Baselines live in `e2e/visual/__baselines__` and are Linux-only, generated inside the
pinned Playwright container:

```sh
docker run --rm --ipc=host -v "$PWD":/work -w /work \
  mcr.microsoft.com/playwright:v1.61.1-noble \
  bash -lc 'corepack enable && pnpm install --frozen-lockfile && \
            DETENT_VRT_CONTAINER=1 pnpm exec playwright test --project=vrt'
```

Add `--update-snapshots` only when a PR states why pixels changed. A bare local `pnpm vrt`
outside the container skips the project by design.
