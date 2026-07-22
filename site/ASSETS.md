# site/ASSETS.md — asset provenance ledger

Every visual asset shipped by the site (and the shared sequence/icon assets) is recorded
here. Policy: original, hand-written SVG only; references may be studied for direction and
must be named; no traced, copied, or auto-generated third-party geometry; no stock, no
clip-art, no AI-image imports. Fonts are the repository's licensed set only. Additions to
this file accompany the PR that adds the asset.

## Fonts

| Asset | Source | License | Note |
|---|---|---|---|
| IBM Plex Sans (400/500/600) | IBM, self-hosted in `site/src/assets/fonts` (synced from `web/`) | OFL-1.1 | already in repo; drift-gated by `sync-fonts.mjs` |
| IBM Plex Mono (400/500) | IBM, self-hosted | OFL-1.1 | machine-voice roles only |

## Marks

| Asset | Author | Date | Provenance |
|---|---|---|---|
| E1 "Convergence Seat" (mark `src/components/Mark.astro`, favicon `public/favicon.svg`, lockup) | FR3→RD3 (in-house), affirmed N4 | 2026-07-21 | Original. D1 core (FR3): geometry derived from ball-detent engineering conventions — 90° V, ~26% seat depth, apex daylight — studied via FIRGELLI "Detent Mechanism", Wikipedia "Ball detent" (facts, not artwork). E1 strokes (RD3): original 45° construction. No third-party geometry. |
| OG social template (`og/template.svg`, 1200×630) | N4 | 2026-07-21 | Original composition of E1 + the One-Way Seat sequence strip; text slots are template variables; hexes from the ratified token set. |
| OG rendered cards (`public/og/og-*.png`, 8 files) | SITE builder from N4's template | 2026-07-21 | Mechanical render of `og/template.svg` via pinned Playwright Chromium with the repo's IBM Plex subsets; hashes pinned in `og/manifest.json`, drift-gated (`scripts/build-og.mjs --check`). |

## The One-Way Seat sequence

| Asset | Author | Date | Provenance |
|---|---|---|---|
| Master stage SVG (12 beats, 720×300 — `src/components/OneWayStage.astro`) | N4 (geometry), SITE builder (state CSS + value interpolation) | 2026-07-21 | Original, hand-plotted integer coordinates. References studied for direction only: the repo's own graph notch/legend (`web/src/features/graph`), engineering-drawing title-block conventions, double-entry bookkeeping's double rule (a typographic convention, not a design), FIRGELLI ratchet/pawl articles (mechanical accuracy of the pawl). No traced geometry. Interpolated values come only from the drift-synced recorded artifact (`src/data/demo/`). |
| Hero poster frame (beat-10 crop, Home) | N4 | 2026-07-21 | Crop of the master stage (`viewBox 120 40 560 240`); no separate geometry. |

## Domain icons (`src/assets/icons/`, 16 files)

| Asset | Author | Date | Provenance |
|---|---|---|---|
| intent, stable-id, persist, gate-allow, gate-deny, boundary, seat-settle, ambiguous, probe, evidence, duplicate-reject, orphan-absence, crash-seam, recovery, ledger, adapter-tier | N4 | 2026-07-21 | Original hand-written paths. Lucide's published grid conventions (24 grid, 2px stroke, round caps) adopted for compatibility; no Lucide path reused, traced, or modified. seat-settle derives from the in-house D1 geometry. Per-file provenance comment embedded in each SVG. Call sites always pair an icon with a visible text label. |

## Product imagery

| Asset | Author | Date | Provenance |
|---|---|---|---|
| Workbench screenshots (`public/images/workbench-*.png`, 4 files) | site task (capture script) | 2026-07-21 | Captured from the running fixture-backed `web/` app at 1440×900 (2× DPR), both themes, SYNTHETIC FIXTURE banner deliberately in frame; re-capture with `scripts/capture-workbench.mjs`. |

## Inline diagram glyphs

| Asset | Author | Date | Provenance |
|---|---|---|---|
| Page-local SVGs (theme sun/moon in `Base.astro`, play triangle on Home, conceptual diagrams on Engine/How-it-works) | in-house (site tasks) | 2026-07-21 | Original primitive geometry (circles, lines, triangles); no third-party paths. |

## Licensing note

The repository currently carries no license (LICENSING.md; ADR-0014 open). These assets are
project-original work recorded for future licensing decisions; nothing here grants or
implies external reuse rights.
