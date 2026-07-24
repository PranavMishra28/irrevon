<!-- GENERATED FILE — DO NOT EDIT BY HAND.
     Source: scripts/third-party.json · Generator: scripts/build-third-party-notices.py
     Drift-gated by `make third-party` (part of `make check`). -->

# Third-party notices

## 0. Scope

This inventory covers the third-party components of the Irrevon artifacts: the
Python wheel/sdist (which embeds the built workbench, ADR-0018), the workbench
build (`web/`), the marketing site build (`site/`), and the vendored fonts.
**Status: staged, pre-release.** No Irrevon artifact has been published and the
project's own code and content are licensed under Apache-2.0 (ADR-0028; see
LICENSE, NOTICE, and LICENSING.md). Third-party redistribution obligations remain
separate from that project license and attach when covered artifacts are
redistributed. Exact upstream license files for every production package
bundled into the Workbench are committed in `THIRD-PARTY-LICENSES.md` and
regenerated from the frozen pnpm production graph during the release dry run.

Dev/test dependencies (sections 5a/5b) are never distributed and appear for
SBOM completeness only. MPL-2.0 items (hypothesis, pathspec, @axe-core/playwright)
are dev-only and unmodified: no obligations attach to any shipped artifact.

## 1. Python wheel/sdist — runtime dependencies
Installed by every user of the packaged artifact; pinned by `uv.lock`.

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `rfc8785` | 0.1.4 (==) | Apache-2.0 | <https://pypi.org/project/rfc8785/> | RFC 8785 (JCS) encoder — Trail of Bits; version-pinned per ADR-0013 |
| `jsonschema` | >=4.25 | MIT | <https://pypi.org/project/jsonschema/> | JSON Schema 2020-12 validation of the trust-boundary contracts |
| `psycopg` | >=3.3.4 | LGPL-3.0-only | <https://pypi.org/project/psycopg/> | Postgres driver; the ONE non-permissive runtime dep — separately installed, never vendored; exception analysis in docs/review-queue.md section 2 (rides ADR-0014 items 7/18) |
| `psycopg-binary` | (extra of psycopg) | LGPL-3.0-only | <https://pypi.org/project/psycopg-binary/> | bundles libpq, which is PostgreSQL License (permissive) |
| `attrs / referencing / rpds-py / jsonschema-specifications` | (transitive, uv.lock-pinned) | MIT | <https://pypi.org/project/jsonschema/> | jsonschema's dependency tree |
| `typing-extensions` | (transitive) | PSF-2.0 | <https://pypi.org/project/typing-extensions/> | permissive |
| `tzdata` | (transitive) | Apache-2.0 | <https://pypi.org/project/tzdata/> | — |

## 2. Embedded workbench bundle (`web/dist` inside the wheel)
ADR-0018 embeds the built workbench in the wheel and sdist — the wheel is a redistribution event for these packages; their license-preservation duties attach to the PyPI artifact, not just the web build.

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `react / react-dom` | 19.2.7 | MIT | <https://react.dev> | ships in web/dist, therefore inside the PyPI wheel (ADR-0018) |
| `@tanstack/react-router` | 1.170.18 | MIT | <https://tanstack.com/router> | shipped |
| `@tanstack/react-query` | 5.101.2 | MIT | <https://tanstack.com/query> | shipped |
| `@tanstack/react-table` | 8.21.3 | MIT | <https://tanstack.com/table> | shipped |
| `@base-ui/react` | 1.6.0 | MIT | <https://base-ui.com> | shipped |
| `lucide-react` | 1.24.0 | ISC | <https://lucide.dev> | attribution-preserving ISC terms; consumed as code via the internal icon registry — no committed icon files |
| `tailwindcss (generated CSS)` | 4.3.3 | MIT | <https://tailwindcss.com> | the generated stylesheet ships; the tool itself is dev-only |

## 3. Fonts — IBM Plex Sans / IBM Plex Mono (OFL-1.1)
Full license text: the `OFL.txt` adjacent to the font files (`web/public/fonts/OFL.txt`, `site/src/assets/fonts/OFL.txt`), copied into built output with them. Local re-subsetting is prohibited without a registry + counsel revisit (would create a Modified Version under the RFN clause).

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `@ibm/plex-sans` | 1.1.0 | OFL-1.1 | <https://github.com/IBM/plex> | upstream-built Latin1 woff2 subsets copied byte-identically by fonts:sync (drift-checked); NOT locally modified or re-subsetted, so the 'Plex' Reserved Font Name clause for Modified Versions is not triggered; OFL.txt travels adjacent to the font files in every distribution |
| `@ibm/plex-mono` | 2.5.0 | OFL-1.1 | <https://github.com/IBM/plex> | same posture as @ibm/plex-sans |

## 4. Marketing site (`site/dist`)
Static HTML/CSS + self-hosted OFL fonts; never ships in the Python wheel.

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `astro` | 7.1.0 | MIT | <https://astro.build> | static output; runtime helpers in built HTML are MIT |
| `@astrojs/sitemap` | 3.7.3 | MIT | <https://docs.astro.build> | — |
| `@astrojs/rss` | 4.0.19 | MIT | <https://docs.astro.build> | — |
| `@astrojs/markdown-satteri` | 0.3.4 | MIT | <https://docs.astro.build> | explicit pin of Astro 7's markdown processor (local plugins import a declared dependency) |
| `@astrojs/check` | 0.9.9 | MIT | <https://docs.astro.build> | dev-only |
| `pagefind` | 1.5.2 | MIT | <https://pagefind.app> | dev-time indexer; the self-hosted search bundle it emits ships in site/dist (loads only on user gesture) |
| `@playwright/test` | 1.61.1 | Apache-2.0 | <https://playwright.dev> | dev-only |
| `@axe-core/playwright` | 4.12.1 | MPL-2.0 | <https://github.com/dequelabs/axe-core-npm> | dev-only, unmodified — no obligations |
| `typescript` | 5.9.3 | Apache-2.0 | <https://www.typescriptlang.org> | dev-only |

## 5a. Dev/test dependencies — Python (never distributed)
SBOM-only; no shipped artifact contains them.

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `pytest` | >=8.4 | MIT | <https://pypi.org/project/pytest/> | — |
| `pytest-xdist` | >=3.8 | MIT | <https://pypi.org/project/pytest-xdist/> | — |
| `hypothesis` | >=6.157 | MPL-2.0 | <https://pypi.org/project/hypothesis/> | weak file-level copyleft; used unmodified as a test dep, never redistributed — no obligations attach (MPL-2.0 §3 triggers on distribution of MPL-covered files) |
| `mypy` | >=1.19 | MIT | <https://pypi.org/project/mypy/> | — |
| `types-jsonschema` | >=4.25 | Apache-2.0 | <https://pypi.org/project/types-jsonschema/> | — |
| `ruff` | >=0.14 | MIT | <https://pypi.org/project/ruff/> | — |
| `import-linter` | >=2.5 | BSD-2-Clause | <https://pypi.org/project/import-linter/> | transitive: grimp (BSD-2), click (BSD-3) |
| `spdx-tools` | 0.8.3 (==) | Apache-2.0 | <https://github.com/spdx/tools-python> | official SPDX 2.3 parser/validator used only by the release dry run; exact-pinned |
| `(other dev transitives)` | (uv.lock-pinned) | MIT / BSD / Apache-2.0 / MPL-2.0 (pathspec) | — | execnet, pluggy, iniconfig, rich, mypy-extensions, markdown-it-py, mdurl (MIT); Pygments (BSD-2); sortedcontainers (Apache-2.0); pathspec (MPL-2.0, unmodified dev-only) |

## 5b. Dev/test dependencies — web (never distributed)
SBOM-only; no shipped artifact contains them.

| Component | Version | License | Homepage | Notes |
|---|---|---|---|---|
| `@playwright/test` | 1.61.1 | Apache-2.0 | <https://playwright.dev> | — |
| `typescript` | 5.9.3 | Apache-2.0 | <https://www.typescriptlang.org> | — |
| `@axe-core/playwright` | 4.12.1 | MPL-2.0 | <https://github.com/dequelabs/axe-core-npm> | dev-only, unmodified — no obligations; SBOM-only |
| `(all other web devDependencies)` | (exact-pinned in web/package.json) | MIT / ISC | — | vite, vitest, storybook, @storybook/react-vite, @storybook/addon-a11y, @storybook/addon-vitest, eslint, eslint-plugin-boundaries, eslint-plugin-jsx-a11y, eslint-import-resolver-typescript, typescript-eslint, @tanstack/eslint-plugin-query, @tanstack/eslint-plugin-router, @tanstack/router-plugin, stylelint, stylelint-declaration-strict-value, prettier, msw, size-limit, @size-limit/preset-app, json-schema-to-typescript, @vitejs/plugin-react, @vitest/browser-playwright, @tailwindcss/vite, @types/node, @types/react, @types/react-dom |
