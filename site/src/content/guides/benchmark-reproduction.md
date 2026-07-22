---
title: "Benchmark reproduction"
description: "The intended reproduction contract for IrrevonBench — published before any run exists, so the promise is inspectable in advance. No results yet, by design."
order: 6
badge: "preregistered"
claims:
  - no-results-exist
  - prereg-draft-status
  - stamping-planned
  - stats-discipline
  - credibility-controls
---

> **PREREGISTERED METHODOLOGY — NO RESULTS YET.** No benchmark run has occurred. There
> is nothing to reproduce today. This page documents the reproduction contract the
> project has committed to *before* the first run, so that when results exist, the
> promise they arrive with was inspectable in advance.

## Why this page exists now

A reproduction story bolted on after results exist is marketing. IrrevonBench's
preregistration is currently a **DRAFT** — nothing is frozen, and no run, sandbox
spike, or fault trial may occur before the Stage-A freeze, which is a human act. The
full design lives in the rendered
[benchmark preregistration](/docs/reference/benchmark-preregistration/); the
[benchmark page](/benchmark/) carries the narrative version, including the
pre-committed falsification criterion.

## The intended reproduction contract

When a benchmark run is published, reproducing it is committed to work through **both**
of these legs (per the distribution decision record,
[ADR-0018](/docs/reference/adr-0018-distribution-model/)):

1. **Locked toolchain from a signed tag.** Check out the signed release tag and
   `uv sync --locked` — the committed `uv.lock` pins the exact dependency set that
   produced the run.
2. **Digest-pinned container.** A reproduction image, referenced by digest (not tag),
   for environments where the host toolchain cannot be trusted to match.

Canonical run artifacts are committed to go to GitHub Releases (working copies) and
Zenodo (archival, DOI) — never parked in expiring CI artifacts.

## What "reproduced" will mean

The statistical discipline is preregistered, not improvised: at least 5 seeds per cell
(10 planned), means with confidence intervals and effect sizes, every executed cell
reported, INVALID runs retained and marked rather than deleted — and a second-machine
reproduction plus independent recomputation of a random 10% of cells before any public
claim.

The fault seeds for the confirmatory stratum come from a **sealed private holdout that
never enters the repository** — so a reproduction of published results exercises the
published seeds, while the holdout guards against the benchmark having been tuned to
its own test.

## What would make this page change

- **Stage-A freeze** (design frozen, hash-stamped, externally timestamped): this page
  gains the freeze hashes and stamp receipts.
- **Stage-B freeze** (adapters, baseline operationalization, artifact hashes): the
  concrete adapter and container digests land here.
- **First published run:** the banner above is replaced by the exact commands, tag,
  digests, and artifact links for that run — nothing else on this page should need to
  change. That is the point of writing it first.
