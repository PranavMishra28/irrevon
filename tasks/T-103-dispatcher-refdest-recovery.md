# T-103: Implement dispatcher, reference destinations, reconciliation, recovery, and sweep

---
id: T-103
status: done             # completed 2026-07-21
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

- [x] Kill-before-persist: SIGKILL at every armed seam; zero destination effects without a
      durable PERSISTED record (refdest truth API + direct SQL oracle); zero tolerance.
- [x] Crash-recovery: restart adjudicates every DISPATCHED/AMBIGUOUS record before any new
      dispatch (refdest request-log order proves it); re-entrant under mid-recovery kills.
- [x] Edge case: absence with a null `consistency.status_settlement_lag` settles LOST but
      auto-routes ESCALATED_HUMAN and refuses `policy_auto` redispatch (RFC-002 §6.2).
- [x] Sweep: K out-of-band effects yield exactly K ORPHANED findings keyed by
      `(adapter_id, destination_ref)`; zero false orphans for in-flight dispatches.
- [x] `make check` and all `py-*` gates pass.

## Required validation

`make check && make py-check py-test py-test-integration`; attach output.

## Documentation updates

This file's status.

## Human review triggers — stop and ask if:

- Any invariant requires weakening a test to pass (never do it; stop instead).
- The taxonomy meets a transport condition RFC-002 §10 cannot classify.

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.

## Completion record (2026-07-21)

- `make check` OK; `make py-check` OK (ruff, mypy strict on 22 src files,
  import-linter); `make py-test` → `63 passed`; `make py-test-integration` →
  `201 passed` (real Postgres 17 + refdest, engine-as-subprocess where required).
- Kill-before-persist (SIGKILL at armed seams, exit −9 asserted): persist.pre_commit
  (fully effect-free), persist.post_commit, gate.post_allow, adapter.pre_call
  (claimed-not-sent), receipt.pre_commit (effect-no-receipt), receipt.post_commit;
  plus the global zero-tolerance oracle (every destination effect maps to a durable
  DISPATCHED record). Oracles: refdest /control/state + direct SQL, never the engine.
- Crash-recovery: flagship response-lost shape (LOST → SIGKILL → restart →
  reconcile-by-query → SETTLED_COMMITTED + CONFIRMED_UNIQUE, request-log proves
  query-before-any-create, zero re-dispatch); re-entrant under
  recovery.after_record:{1,2} kills over a 3-record truth split; second engine
  process refused by the boot advisory lock (exit 3).
- Races (sync points, no sleeps): dispatch-vs-reconcile (pinned at
  reconcile.pre_settle → retry sees pending_reconciliation, one settle, count 1),
  reconcile-vs-in-flight-dispatch (skipped_young, no premature LOST),
  sweep-vs-dispatch (no false orphan; OOB still caught), sweep-vs-SIGKILLed
  dispatcher (exactly one finding across both detection paths).
- Reconciliation: C2 PRESENT(1)→CONFIRMED_UNIQUE, PRESENT(n>1)→DUPLICATE(excess),
  confirmed absence (two reads)→LOST, lag gating (PT1H parks), null-lag settle +
  auto-ESCALATED_HUMAN + policy_auto refusal, INDETERMINATE parks, settled records
  re-queried never; C1 in-window replay probe (same key, no second effect);
  C3 parks + escalates, human-only settle; audit mode → DUPLICATE / CONTRADICTED
  (both directions), incl. the §6.2 residual race.
- Taxonomy: Hypothesis property over arbitrary (status, body) — everything not
  positively recognized maps LOST, never FAILED; FAILED only on the two
  declaration-cited shapes; wire-drop → LOST; deadline → TIMEOUT; failed query →
  INDETERMINATE never ABSENT; C2 same-request-twice ⇒ two effects (the honesty
  observation); refdest determinism under seed.
- Recorded deviation from the RFC-002 §2.2 DDL sketch:
  `dispatch_attempts.gate_decision_id` is nullable exactly for kind
  `c1_replay_probe` (CHECK-coupled) — replay probes run under the claim
  discipline but never under the gate (C1 M16).
