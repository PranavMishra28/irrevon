"""IrrevonBench harness — the benchmark foundation layer (preregistration-shaped).

Package discipline:

- The preregistration (docs/benchmark-preregistration.md) is the design authority;
  this package implements its **mechanisms** (formats, seed derivation, fault
  orchestration, oracle read-back, metrics, statistics, invalid-run rules,
  resumable execution) without deciding any human freeze parameter (§0.1) and
  without producing confirmatory observations before the Stage-A freeze.
- Every result produced pre-freeze is labeled ``non-confirmatory`` at the schema
  level (bench-result.schema.json makes an unlabeled pre-freeze result invalid).
- ``irrevon.bench.arms`` (systems under test) MUST NOT import
  ``irrevon.bench.oracle`` — no arm may see oracle/truth data (import-linter
  enforced; the anti-cheating rule of the preregistration and MLPerf-style
  closed-division discipline).
- Benchmark mode never runs with test hooks armed (irrevon.testhooks arming
  rule; recorded per run in the environment manifest).
"""

from __future__ import annotations

HARNESS_VERSION = "0.1.0"

__all__ = ["HARNESS_VERSION"]
