# T-104: Assemble the flagship demo, first-slice CLI, and E2E acceptance test

---
id: T-104
status: draft
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

- [ ] `detent demo` exits 0: Detent leg ends with 1 destination effect, a reconciled
      SETTLED_COMMITTED + CONFIRMED_UNIQUE, and an evidenced dedup deny for the
      re-synthesized retry; B5 leg produces 2 destination effects, proven by read-back.
- [ ] Edge case: the E2E test **fails** if the B5 leg does not duplicate (direction pinned
      in a comment citing §8.6) — verified by a test-of-the-test with keys honored.
- [ ] `detent inspect <effect_id>` shows timeline, deny evidence, and a passing integrity
      section (recomputed `intent_id` matches); values redacted by default.
- [ ] `detent doctor` is read-only (no writes; no network without `--probe`); identity
      self-test reproduces the pinned vectors.
- [ ] Classifier-isolation conformance test green (import-linter + type-level, RFC-002 §14).
- [ ] All gates pass; quickstart from clean checkout ≤15 min.

## Required validation

All make gates; `detent demo --jsonl` summary line + E2E evidence bundle path attached.

## Documentation updates

README quickstart section (install → demo → inspect); this file's status.

## Human review triggers — stop and ask if:

- The B5 contrast leg fails to duplicate (premise problem — escalate, never patch the leg).
- Any CLI surface addition beyond the four commands seems needed (scope decision).

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.
