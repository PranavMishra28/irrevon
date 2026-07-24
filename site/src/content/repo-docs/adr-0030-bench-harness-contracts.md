---
title: "IrrevonBench foundation — benchmark contracts, harness architecture, and integrity gates"
sourcePath: "docs/decisions/0030-bench-harness-contracts.md"
sourceSha256: "e34c75a3292e3e316a58823d532cf77b381cf55dac53ed9702aa29167bc44e1a"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0030"
  status: "proposed"
  date: "2026-07-22"
  supersedes: "—"
---

## Context

The preregistration (DRAFT) defines the benchmark's science but named its
machine-readable formats and harness as future artifacts (§3.1: "field-level
schemas are Stage-B artifacts"; RFC-002 §12 deferred `bench smoke`/`bench run`
to M5/M7). The owner's 2026-07-22 directive ordered the missing benchmark
foundation built now — everything that can exist without violating the
preregistration freeze discipline: contracts, deterministic fixtures, fault
orchestration, oracle, metrics, statistics, invalid-run handling, resumable
execution, contamination controls, and CLI — with human freeze parameters
never chosen silently and no confirmatory observation possible pre-freeze.
Schema admission requires an ADR (contracts rule; ADR-0019/0021 precedent).

## Decision

1. **Seven benchmark contracts** are admitted to `schemas/` as JSON Schema
   2020-12 resources with valid/invalid example suites:
   `bench-workload` / `bench-variants` / `bench-fault-schedule` /
   `bench-manifest` (fixture side, preregistration §3.1) and
   `bench-run-manifest` / `bench-result` / `bench-environment` (execution
   side, §8). Design choices encoded in the schemas rather than in prose:
   dev-split artifacts cannot claim `frozen`; a frozen variant set without a
   passed §3.2 human spot-check is unrepresentable; a holdout manifest
   outside the sealed archive cannot carry the master seed; a
   non-confirmatory result must be labeled `non-confirmatory`; INVALID
   requires one of the three §6 harness-invalid classes; structurally
   undefined metric cells carry marks (`N/A`, `N/A-by-arm`,
   `NOT-DETECTABLE`, `expected-null`, `fixture-truth-only`), never zeros.
   The Extended track's LLM-embedded subjects additionally get a per-trial
   `refused` arm outcome (subject declined ≠ system suppressed: a refusal on
   a legitimate eligible trial reads back as a lost legitimate effect and is
   NEVER counted as false suppression) and an optional per-run
   `subject_accounting` block (refusals, verbalized eval-awareness,
   suspected sandbagging — descriptive diagnostics reported alongside
   results, never pooled into §4 metrics; evaluation-awareness posture in
   docs/benchmark.md §10).
2. **Byte-level pinnings** left open by the preregistration are fixed here:
   (a) §3.4 seed derivation concatenation uses UTF-8 fields joined by the
   ASCII unit separator 0x1F (removes cross-field ambiguity; pinned vectors
   in `tests/bench/test_seeds.py`); (b) seeds are carried in documents as
   decimal strings because 64-bit values exceed the RFC 8785 safe-integer
   domain; (c) artifact digests are SHA-256 over JCS canonical bytes, and the
   manifest root hash is SHA-256 over the JCS bytes of the sorted
   [path, sha256] pairs.
3. **The harness lives in `src/irrevon/bench/`** beside the engine (RFC-002
   §14 pattern), with a hard anti-cheating boundary: `irrevon.bench.arms`
   (systems under test) is forbidden by import-linter from importing the
   oracle, fixtures, metrics, analysis, or runner; the engine is forbidden
   from importing `irrevon.bench` at all; episodes handed to arms carry no
   fixture labels. `scripts/check-bench-integrity.py` (stdlib-only, in
   `make check`) adds manifest-drift, canary, holdout-leakage,
   freeze-honesty, and oracle-token checks over committed files.
4. **The public dev split** is committed under `bench/fixtures/dev/`,
   generated deterministically from a PROVISIONAL nothing-up-my-sleeve master
   seed (SHA-256 of a documented string) and drift-gated against
   regeneration. Freezing or replacing that seed is a Stage-B human act
   (review queue). The holdout sealing mechanism is implemented, tested only
   with synthetic data, and refuses to write inside the repository.
5. **Execution discipline** implements preregistration §6/§8 mechanically:
   write-ahead run manifests; duplicate-execution prevention; interrupted
   runs finalized harness-INVALID and replaced same-seed at most twice per
   slot; harness-invalid as the only INVALID class; sanitized (digest-only)
   evidence bundles; environment capture per run. `irrevon bench run
   --confirmatory` is an integrity refusal (exit 4) unless a human Stage-B
   freeze record exists under `docs/registrations/stage-b-v1/` AND fixtures
   are frozen — and even then the current build refuses, because the
   confirmatory execution plan (arm order, trial counts) is a Stage-B
   artifact this code must consume, not invent.
6. **Statistics and verdicts** (§5) are stdlib-only, pinned by known-answer
   tests against published values; equivalence margins, the worst-cell gate,
   and alphas are required arguments everywhere (§0.1 human parameters have
   no code defaults). Verdict output is labeled non-confirmatory pre-freeze
   unconditionally.

## Alternatives

- *Wait for Stage-B to write any schema/harness* — rejected: the §0
  freeze-preconditions checklist itself requires analysis code written
  against synthetic data and hashed artifacts to exist before Stage-B can
  freeze them; building the mechanism now is what makes a clean freeze
  possible.
- *Adopt a third-party eval framework as the harness* — rejected for the core
  (see ADR-0031); no surveyed framework supports an arbitrary
  agent-system-under-test with an external destination read-back oracle.
- *YAML-authored fixtures* (prereg §3.1 wording) — generated canonical JSON
  only; YAML authoring applies to hand-written workloads, which do not exist
  yet; revisit at Stage-B if humans hand-author workloads.
- *Integer seeds in documents* — rejected; breaks JCS (I-JSON safe-integer
  domain).

## Consequences

Easier: Stage-A/Stage-B freezes now have concrete artifacts to freeze; CI has
a fast benchmark regression mode (`make bench-smoke`, conventional arms, no
DB); companies get a documented private-adoption path sharing the public
contracts (docs/benchmark.md §11). Harder: seven more schemas under the
ADR-first change rule; the dev fixture drift gate makes any generator change
a visible, reviewable fixture diff. Conformance tests: `tests/bench/` (~120
tests incl. baseline-strength locks and the integrity-refusal pin),
import-linter contracts, `make bench-integrity`.

## Risks

The dev master seed is provisional — if the human replaces it at Stage-B,
committed dev fixtures regenerate (visible, mechanical, low blast radius).
The in-process crash simulation for arm R is weaker than SIGKILL (recorded as
a known deviation in every R run manifest; kernel-kill coverage stays in
tests/process/). B4 is mechanically identical to B3 against refdest (recorded
in its spec deviations; differs against real destinations at M4).

## Reopen trigger

Stage-B freeze (formats become frozen artifacts — any shape change thereafter
is an amendment, not an ADR edit); or the M4 real-sandbox adapters
demonstrating that a contract cannot represent a real destination's
capability semantics.
