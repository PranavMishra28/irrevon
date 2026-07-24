---
title: "Benchmark reproduction"
description: "The intended IrrevonBench reproduction contract, with synthetic development pilots disclosed and no live-sandbox or confirmatory result yet."
order: 6
badge: "preregistered"
claims:
  - no-results-exist
  - prereg-draft-status
  - developmental-pilot-disclosure
  - stamping-planned
  - stats-discipline
  - credibility-controls
---

> **DRAFT METHODOLOGY — NO SCIENTIFIC RESULTS YET.** Synthetic S-REF harness and
> fault-smoke pilots have occurred and are disclosed as non-confirmatory engineering
> evidence. No live-sandbox observation or confirmatory run has occurred, so there is no
> scientific result to reproduce today. This page publishes that future reproduction
> contract before either evidence class begins.

## Why this page exists now

A reproduction story bolted on after results exist is marketing. IrrevonBench's
preregistration is currently a **DRAFT** — nothing is frozen. It discloses the prior
synthetic S-REF development pilots rather than claiming a pristine pre-observation design.
Stage A must precede every live-sandbox observation, and Stage B every confirmatory run;
both freezes are human acts. The full design lives in the rendered
[benchmark preregistration](/docs/reference/benchmark-preregistration/); the
[benchmark page](/benchmark/) carries the narrative version, including the
pre-committed falsification criterion.

## The intended reproduction contract

When a benchmark run is published, reproducing it is committed to work through **both**
of these legs (per the distribution decision record,
[ADR-0018](/docs/reference/adr-0018-distribution-model/)):

1. **Locked toolchain from an annotated release tag.** Check out the annotated
   release tag, verify the GitHub artifact attestation, and `uv sync --locked` —
   the committed `uv.lock` pins the exact dependency set that produced the run.
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
