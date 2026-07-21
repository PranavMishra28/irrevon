# T-104: Assemble the flagship demo, first-slice CLI, and E2E acceptance test

---
id: T-104
status: done             # completed 2026-07-21
depends_on: [T-103]
invariant: "master doc §8.3 — the B5 contrast leg is never weakened so the demo wins"
---

## Objective

The runnable first public artifact: `detent init`/`doctor`/`demo`/`inspect`, JSONL logging,
and the two-leg E2E test (Detent + B5 contrast) implementing RFC-001 §9's acceptance script.

## Why

RFC-001's acceptance test is the slice's definition of done (master doc §16, item 6); the
CLI is four commands for the first slice (RFC-002 §12); bench commands arrive at M5/M7.

## Context — read these first

- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §3 (demo story), §9 (tests)
- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §5.2, §11, §12

## Scope

**Allowed to write:** `src/detent/{cli,api,advisory,logging}/**` (advisory = the isolation
seam only, no classifier), `tests/e2e/**`, the `init`-written templates, this file's status.
**Forbidden:** `bench` commands, `serve`, real-sandbox anything, CI workflows, `web/`.

## Acceptance criteria

- [x] `detent demo` exits 0: Detent leg ends with 1 destination effect, a reconciled
      SETTLED_COMMITTED + CONFIRMED_UNIQUE, and an evidenced dedup deny for the
      re-synthesized retry; B5 leg produces 2 destination effects, proven by read-back.
- [x] Edge case: the E2E test **fails** if the B5 leg does not duplicate (direction pinned
      in a comment citing §8.6) — verified by a test-of-the-test with keys honored.
- [x] `detent inspect <effect_id>` shows timeline, deny evidence, and a passing integrity
      section (recomputed `intent_id` matches); values redacted by default.
- [x] `detent doctor` is read-only (no writes; no network without `--probe`); identity
      self-test reproduces the pinned vectors.
- [x] Classifier-isolation conformance test green (import-linter + type-level, RFC-002 §14).
- [x] All gates pass; quickstart from clean checkout ≤15 min.

## Required validation

All make gates; `detent demo --jsonl` summary line + E2E evidence bundle path attached.

## Documentation updates

README quickstart section (install → demo → inspect); this file's status.

## Human review triggers — stop and ask if:

- The B5 contrast leg fails to duplicate (premise problem — escalate, never patch the leg).
- Any CLI surface addition beyond the four commands seems needed (scope decision).

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.

## Completion record (2026-07-21)

- `detent demo --jsonl` summary line (seed 777, real SIGKILL crash between legs):
  `{"schema_version": "1", "seed": 777, "detent_leg": {"destination_effects": 1,
  "duplicate_rejected": true, "reconciled": "SETTLED_COMMITTED", "effect_id":
  "0bb7e8d6…7caf"}, "b5_leg": {"destination_effects": 2, "duplicate_created": true},
  "contrast_holds": true}` — exit 0. (The demo fixture is the T-000 v2 intent tuple, so
  the printed effect_id equals the cross-language conformance digest.)
- E2E evidence: `tests/e2e/test_flagship.py` — leg R steps 1–10 with per-step SQL +
  truth-API assertions (incl. an in-test independent identity derivation as the step-1
  oracle) and the PINNED B5 assertion (fails the build if B5 does not duplicate; §8.6
  cited in the comment); test-of-the-test runs the same B5 against the key-honoring C1
  profile and shows the predicate correctly goes false.
- CLI: `init` (templates + idempotent migrations), `doctor` (read-only, exit 3 on
  failures, identity self-test against the pinned vectors, mutation-free verified by
  row counts), `demo` (`--seed/--leg/--keep/--jsonl`; exit 3 if the contrast fails),
  `inspect` (timeline, receipts, gate history, probes, findings + resolutions,
  integrity recomputation; values redacted without `--reveal`; exit 3 not-found,
  exit 4 integrity mismatch). JSONL logging per RFC-002 §11 (stderr, stable event
  catalog, no decision path reads logs).
- Classifier isolation: import-linter contract "advisory is never on the authority
  path" (2 contracts kept) + marker/type-level rejection at every mutation API incl.
  serialized round-trip laundering; ledger byte-unchanged after every attempt.
- Gates: `make check` OK; `make py-check` OK (ruff + mypy strict + import-linter,
  2 contracts kept); `make py-test` 63 passed; `make py-test-integration` 217 passed.
  Quickstart commands documented in README (measured well under 15 min).
