# site/ASSETS.md — pointer to the root asset registry

Asset provenance is recorded **once**, in the repository-root [ASSETS.md](../ASSETS.md)
(generated from `scripts/assets-registry.json`, drift-gated by `make assets` inside
`make check`: byte-parity, per-file sha256, and a coverage sweep that includes
`site/public/`, `site/src/assets/`, and `site/og/`). Add or replace a site asset by
adding/updating its registry row there — an unregistered asset fails CI.

Provenance for geometry embedded in site components (not standalone asset files, so
outside the sweep):

- **The One-Way Seat master stage** (`src/components/OneWayStage.astro`, 12 beats,
  720×300): original, hand-plotted integer coordinates. References studied for
  direction only: the repo's own graph notch/legend (`web/src/features/graph`),
  engineering-drawing title-block conventions, double-entry bookkeeping's double rule
  (a typographic convention, not a design), FIRGELLI ratchet/pawl articles (mechanical
  accuracy of the pawl). No traced geometry; interpolated values come only from the
  drift-synced recorded artifact (`src/data/demo/`). The Home hero poster is a crop of
  this stage (`viewBox 120 40 560 240`) — no separate geometry.
- **Page-local inline SVGs** (theme sun/moon in `Base.astro`, play triangle on Home,
  conceptual diagrams on Engine/How-it-works): original primitive geometry (circles,
  lines, triangles); no third-party paths.

Policy (unchanged): original, hand-written SVG only; references may be studied for
direction and must be named; no traced, copied, or auto-generated third-party
geometry; no stock, no clip-art, no AI-image imports. Fonts are the repository's
licensed set only.
