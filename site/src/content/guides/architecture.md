---
title: "Architecture"
description: "The engine's components and the three-dimension state model — a guided narrative over the canonical design documents, with links into each."
order: 5
badge: "conceptual"
claims:
  - components-responsibilities
  - state-model
  - classifier-advisory
  - single-writer-scope
  - recovery-adjudicate
---

This guide is a narrative over the canonical design documents — it cites them rather
than restating them. The authoritative mechanics live in
[RFC-002 — engine design](/docs/reference/rfc-002/); the product-level architecture and
invariants live in the master document (linked from the [docs landing](/docs/), §6–§7).

## The pipeline

Every irreversible action moves through the same stations, in order:

```text
agent tool call
      │
      ▼
Intent Registrar ──► Effect Ledger ──► Commit Gate ──► Dispatcher ──► destination
   (validate,          (persist,         (deny-list,      (cross the
    derive identity)    append-only)      authority,       boundary
                                          lineage,         at most once)
                                          dedup)
                            ▲
                            │ evidence, always
      Reconciliation Engine + Orphan Sweep ◄── destination read-back
```

- **Intent Registrar** — validates the intent contract (the trust boundary) and derives
  effect identity from stable business identifiers, never model output.
- **Effect Ledger** — the append-only record; state transitions are locked SQL
  functions, so an illegal transition is a database error, not a code-review hope.
- **Commit Gate** — the only door to a dispatch. Four recorded checks (deny-list,
  authority, branch lineage, dedup); a DENY cites the evidence that blocked it.
- **Dispatcher** — crosses the boundary at most once per allowed claim and records a
  receipt for every attempt, including the ones that vanish.
- **Reconciliation Engine + Orphan Sweep** — resolves ambiguity by querying the
  destination's authoritative status, and pairs destination-side effects with ledger
  records; an effect with no ledger partner becomes an orphan **finding**.
- **Adapters** — capability-tiered bindings to destinations (see
  [adapter development](/docs/adapter-development/)).
- **Outcome Classifier** — advisory only, and architecturally unable to reach the gate
  or resolve APIs: import direction is linter-enforced and its output is a proposal
  type no mutation API accepts. Model output carries no authority anywhere.

## The three-dimension state model

One enum cannot describe an irreversible effect honestly, so the state is three
orthogonal dimensions:

| Dimension | Values | What it answers |
|---|---|---|
| A — execution lifecycle | INTENDED → PERSISTED → DISPATCHED → SETTLED / AMBIGUOUS / CANCELLED | What did we do? |
| B — reconciliation classification | UNRECONCILED · CONFIRMED_UNIQUE · DUPLICATE · LOST · CONTRADICTED · ORPHANED | What does the destination say happened? |
| C — resolution status | OPEN → … → CLOSED | What has a human (or policy) decided about the discrepancy? |

Orphans are representable **only** as findings — a ledger-keyed state machine cannot
express "the destination has something we never recorded," and pretending otherwise is
how orphans get lost. The ratified state tables are encoded once, in
`src/irrevon/statetable.py`, and everything else (schema enums included) is generated
from them, never hand-copied.

## Recovery, the part that earns the ledger

On every boot the engine takes a single-writer advisory lock (refusing to start if
another writer holds it — a documented POC scaling limit), then replays the ledger:
every `DISPATCHED` or `AMBIGUOUS` record is adjudicated against the destination
**before** any new dispatch of the same operation. Re-dispatch requires confirmed
absence plus fresh authority. Never re-dispatch on belief — that rule is the reason the
flagship demo's crash leg ends with one destination effect instead of two.

## Module boundaries

The implementation is a modular monolith: `identity` (pure, no I/O), `contract`,
`ledger` (the only module with SQL), `gate`, `dispatcher`, `reconciler`, `sweep`,
`resolution`, `recovery`, `adapters` (the only wire I/O), `advisory`, and `api` (the
composition root). Import direction is CI-enforced. RFC-002 §14 is the canonical
statement of these boundaries.
