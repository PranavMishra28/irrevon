# T-103: Implement dispatcher, reference destinations, reconciliation, recovery, and sweep

---
id: T-103
status: draft
depends_on: [T-102]
invariant: "master doc §7.4 item 2 — adjudicate before redispatch; unknown outcomes are AMBIGUOUS, never FAILED"
---

## Objective

The wire half of the engine: claim protocol + dispatcher, reference destinations (C2/C3
profiles), reconciliation with calibrated confirmed-absence, crash-recovery replay, and the
orphan sweep — with kill-before-persist and crash-recovery conformance tests green.

## Why

Completes the slice mechanics so T-104 can assemble the flagship demo; RFC-002 §§5–8, 10,
13 pin every semantic here, incl. the three non-initial claim operations.

## Context — read these first

- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §5–§8, §10, §13,
  §15 items 2–4
- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §5–§7, §10

## Scope

**Allowed to write:** `src/detent/{dispatcher,reconciler,sweep,resolution,recovery,adapters}/**`,
refdest capability declarations (data + schema examples), `tests/**`, this file's status.
**Forbidden:** real-sandbox adapters (M4, post ADR-0012), CLI (T-104), CI, bench harness.

## Acceptance criteria

- [ ] Kill-before-persist: SIGKILL at every armed seam; zero destination effects without a
      durable PERSISTED record (refdest truth API + direct SQL oracle); zero tolerance.
- [ ] Crash-recovery: restart adjudicates every DISPATCHED/AMBIGUOUS record before any new
      dispatch (refdest request-log order proves it); re-entrant under mid-recovery kills.
- [ ] Edge case: absence with a null `consistency.status_settlement_lag` settles LOST but
      auto-routes ESCALATED_HUMAN and refuses `policy_auto` redispatch (RFC-002 §6.2).
- [ ] Sweep: K out-of-band effects yield exactly K ORPHANED findings keyed by
      `(adapter_id, destination_ref)`; zero false orphans for in-flight dispatches.
- [ ] `make check` and all `py-*` gates pass.

## Required validation

`make check && make py-check py-test py-test-integration`; attach output.

## Documentation updates

This file's status.

## Human review triggers — stop and ask if:

- Any invariant requires weakening a test to pass (never do it; stop instead).
- The taxonomy meets a transport condition RFC-002 §10 cannot classify.

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.
