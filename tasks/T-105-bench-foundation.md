# T-105: Build the IrrevonBench foundation layer (one branch, one PR)

---
id: T-105
status: done
depends_on: [T-101, T-102, T-103, T-104]
invariant: "master doc §8 (benchmark design; baselines never weakened; oracle exactness) + preregistration §0 (no confirmatory observation pre-freeze; freeze parameters human-only)"
---

## Objective

Implement the complete reversible benchmark foundation the preregistration
requires — contracts, fixtures, fault orchestration, oracle, metrics,
statistics, invalid-run handling, resumable execution, contamination
controls, CLI, docs, ADRs — as one reviewable PR, without violating any
freeze discipline.

## Why

Owner directive 2026-07-22 ("Complete IrrevonBench End-to-End in One Pull
Request"), coordinated as a single bounded session. The §0
freeze-preconditions checklist needs these mechanisms to exist before Stage-A
/ Stage-B can freeze anything.

## Context — read these first

- docs/benchmark-preregistration.md (all sections; DRAFT)
- docs/master-doc.md §8 (via the hash-pinned file; never edited)
- docs/rfc-002-engine-design.md §8, §12, §14
- .cursor/rules/benchmark-integrity.mdc

## Scope

**Allowed to write:** `schemas/bench-*` + examples, `src/irrevon/bench/`,
`src/irrevon/cli/` (bench subcommand wiring), `bench/`, `tests/bench/`,
`scripts/check-bench-integrity.py`, `Makefile` (append), `pyproject.toml`
(lint/import-linter config only — zero new dependencies), `docs/benchmark.md`,
`docs/decisions/0030-*`/`0031-*` + index, `docs/ci.md`, `schemas/README.md`,
`AGENTS.md` (map row), `docs/review-queue.md` (append), preregistration DRAFT
additions (§3.4 pin note, §3.5 canary), `.gitignore`, this file.

**Forbidden:** master doc; accepted ADRs beyond status lines; any FROZEN
content; holdout material anywhere; new runtime dependencies; any publication
act; `docs/registrations/` (human-only); weakening any existing gate or test.

## Acceptance criteria

- [x] `make check` exits 0 (incl. the new `bench-integrity` gate)
- [x] `make py-check` exits 0 (ruff, strict mypy, 4 import-linter contracts kept)
- [x] `make py-test` exits 0 (incl. ~120 tests in tests/bench/)
- [x] `make py-test-integration` exits 0 (incl. arm-R episodes + R-vs-B5 contrast locks)
- [x] `make bench-smoke` exits 0 (CLI end-to-end, no DB)
- [x] Failure case: `irrevon bench run --fixtures bench/fixtures/dev` exits 4
      with "INTEGRITY REFUSAL" (pre-freeze guard; pinned in tests/bench/test_cli.py)
- [x] Failure case: a tampered fixture fails `irrevon bench fixtures --verify`
      (exit 3) and `make bench-integrity` (exit 1)

## Required validation

Exact commands: `make check`, `make py-check`, `make py-test`,
`make py-test-integration`, `make bench-smoke`. Output attached to the PR.

## Documentation updates

docs/benchmark.md (new), bench/README.md + bench/PUBLISHING.md +
bench/runs/README.md (new), ADR-0030/0031 + decisions index, schemas/README.md,
docs/ci.md, AGENTS.md map row, review-queue items 32–35 + §2 notes,
preregistration §3.4 pin note + §3.5 canary (DRAFT additions).

## Human review triggers — stop and ask if:

- Any change would touch a FROZEN artifact, choose a §0.1 parameter, create
  `docs/registrations/`, or require a live-sandbox call. (None occurred.)

## Definition of done

All criteria checked; validation output attached to the PR; one branch, one
PR; review-queue items appended for everything human-gated.
