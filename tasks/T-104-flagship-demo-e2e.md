# T-104: Assemble the flagship demo, first-slice CLI, and E2E acceptance test

---
id: T-104
status: draft
depends_on: [T-103]
invariant: "master doc §8.3 — the B5 contrast leg is never weakened so the demo wins"
---

## Objective

The runnable first public artifact: `detent init` / `doctor` / `demo` / `inspect`, JSONL
structured logging, and the automated two-leg E2E test (Detent leg + B5 contrast leg)
implementing RFC-001 §9's acceptance script against the reference destination.

## Why

RFC-001's acceptance test is the slice's definition of done (master doc §16, item 6: the
lost-response + crash + re-synthesized retry that B5 mishandles and Detent reconciles).
The CLI surface is deliberately trimmed to four commands for the first slice
(RFC-002 §12); bench commands arrive at M5/M7.

## Context — read these first

- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §3 (demo story), §9 (test
  plan incl. the B5 contrast leg)
- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §11 (logging +
  inspect), §12 (CLI conventions, exit codes), §5.2 (the evidenced dedup deny the demo
  must surface)

## Scope

**Allowed to write:** `src/detent/{cli,api,advisory}/**` (advisory = the isolation seam
only, no classifier), `src/detent/logging/**`, `tests/e2e/**`, `compose.yaml` template +
`detent.toml` template + `.env.example` written by `init`, this file's status.
**Forbidden:** `bench` commands, `serve`, real-sandbox anything, CI workflows, `web/`.

## Acceptance criteria

- [ ] `detent demo` exits 0: Detent leg ends with 1 destination effect, a reconciled
      SETTLED_COMMITTED + CONFIRMED_UNIQUE, and an evidenced dedup deny for the
      re-synthesized retry; B5 leg produces 2 destination effects, proven by read-back.
- [ ] Edge case: the E2E test **fails** if the B5 leg does not duplicate (assertion
      direction pinned in a code comment citing master doc §8.6) — verified by mutating
      the refdest profile to honor keys in a test-of-the-test.
- [ ] `detent inspect <effect_id>` shows the timeline, deny evidence, and a passing
      integrity section (recomputed `intent_id` matches); values redacted by default.
- [ ] `detent doctor` is read-only (no ledger writes, no network without `--probe`) and
      the identity self-test reproduces the pinned vectors on this machine.
- [ ] Classifier-isolation conformance test green (import-linter + type-level, RFC-002 §14).
- [ ] `make check` and all `py-*` gates pass; quickstart from clean checkout ≤15 min.

## Required validation

`make check && make py-check py-test py-test-integration`; run `detent demo --jsonl` and
attach the summary line + the E2E evidence bundle path.

## Documentation updates

README quickstart section (install → demo → inspect); this file's status.

## Human review triggers — stop and ask if:

- The B5 contrast leg fails to duplicate (premise problem — escalate, never patch the leg).
- Any CLI surface addition beyond the four commands seems needed (scope decision).

## Definition of done

All criteria checked; validation output attached; documentation updates made; no writes
outside allowed scope; status set.
