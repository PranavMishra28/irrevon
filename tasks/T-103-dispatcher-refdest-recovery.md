# T-103: Implement dispatcher, reference destinations, reconciliation, recovery, and sweep

---
id: T-103
status: draft
depends_on: [T-102]
invariant: "master doc §7.4 item 2 — adjudicate before redispatch; unknown outcomes are AMBIGUOUS, never FAILED"
---

## Objective

The wire half of the engine: claim protocol + dispatcher, the deterministic reference
destinations (C2 and C3 profiles), transport taxonomy, reconciliation with calibrated
confirmed-absence, crash-recovery replay, and the orphan sweep — with the
kill-before-persist and crash-recovery conformance tests green.

## Why

Completes the RFC-001 slice mechanics so T-104 can assemble the flagship demo. RFC-002
§§5–8, 10, 13 pin every semantic this task implements, including the three explicit
non-initial claim operations (validity-review fix M2).

## Context — read these first

- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §5 (dispatch/retry/
  replay), §6 (reconciliation, absence calibration), §7 (recovery, sweep, compensation),
  §8 (reference destinations), §10 (taxonomy), §13 (concurrency), §15 items 2–4
- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §5–§7, §10

## Scope

**Allowed to write:** `src/detent/{dispatcher,reconciler,sweep,resolution,recovery,adapters}/**`,
the refdest capability declarations (as data + schema examples), `tests/**`, this file's
status.
**Forbidden:** real-sandbox adapters (M4, post ADR-0012 close), CLI surface (T-104), CI
workflows, benchmark harness.

## Acceptance criteria

- [ ] Kill-before-persist: SIGKILL at every armed seam; zero destination effects without a
      durable PERSISTED record (refdest truth API + direct SQL oracle); zero tolerance.
- [ ] Crash-recovery: for each seam, restart adjudicates every DISPATCHED/AMBIGUOUS record
      before any new dispatch (refdest request-log order proves status-query-before-
      redispatch); recovery is re-entrant under repeated mid-recovery kills.
- [ ] Edge case: confirmed-absence with a null `consistency.status_settlement_lag` settles
      LOST but auto-routes ESCALATED_HUMAN and refuses `policy_auto` redispatch
      (RFC-002 §6.2).
- [ ] Sweep: K out-of-band effects yield exactly K ORPHANED findings keyed by
      `(adapter_id, destination_ref)`; zero false orphans for in-flight dispatches
      (open-attempt guard); two-pass grace honored.
- [ ] `make check` and all `py-*` gates pass.

## Required validation

`make check && make py-check py-test py-test-integration`; attach output.

## Documentation updates

This file's status; any declared-vs-observed refdest deviation recorded (none expected —
the refdest is ours).

## Human review triggers — stop and ask if:

- Any invariant requires weakening a test to pass (never do it; stop instead).
- The taxonomy meets a transport condition RFC-002 §10 cannot classify.

## Definition of done

All criteria checked; validation output attached; documentation updates made; no writes
outside allowed scope; status set.
