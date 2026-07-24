---
title: "Integration guide"
description: "Wiring Irrevon into an agent's tool boundary: register_intent then dispatch, with reconcile, sweep, and resolve driven by the library."
order: 3
claims:
  - identity-stable-ids
  - persist-before-dispatch
  - reconcile-by-query
  - trust-boundary
  - thirty-min-target
---

The integration surface is deliberately thin: a wrapper at the tool-call boundary. Your
agent calls `register_intent` and then `dispatch`; reconciliation, recovery, sweeping,
and resolution are library-driven. The stated target — a stranger integrates against one
sandbox in under 30 minutes — is a target with a test (the stranger test), not an
achievement yet.

## The two calls your code makes

```python
from irrevon.api import Engine

with Engine(dsn, {"refdest-c2": adapter}) as engine:
    engine.boot()   # writer lock + crash-recovery replay, BEFORE any work

    registration = engine.register_intent({
        "schema_version": "1",
        "effect_type": "order.create",
        "scope": "acme-store/prod",
        "stable_ids": {"order_id": "...", "customer_ref": "..."},
        "adapter_id": "refdest-c2",
        "parameters": {...},         # validated, never part of identity
        "event_time": "...",
    })

    report = engine.dispatch(registration.effect_id)
```

The payload above is the **intent contract** — the trust boundary. Nothing
model-generated crosses into the deterministic core except through this validated
contract, and identity derives only from `stable_ids + effect_type + scope`. The
`parameters` a model re-synthesizes on retry can change every byte; the identity cannot.

Field shapes are machine-checked: see the
[schemas contract map](/docs/reference/schemas/) and the intent-contract schema's
valid/invalid example suites, which CI enforces.

## What the engine does with them

1. **`register_intent`** validates the contract, derives the identity hash, and writes a
   durable `PERSISTED` record — before anything is sent. A crash before this point is
   provably effect-free. A replayed registration with the same stable identity returns
   the same `effect_id` (`registration.replayed` tells you which happened).
2. **`dispatch`** runs the commit gate (deny-list, authority, branch lineage, dedup —
   each check recorded with evidence), then crosses the boundary at most once. The
   report carries the gate outcome; a denied dispatch is an evidenced decision, not an
   exception.
3. **Ambiguity is a recorded state, not an error.** A lost response parks the record as
   `AMBIGUOUS`. Recovery — on `boot()` after a crash, or via `reconcile` — resolves it
   by querying the destination's authoritative status, never by believing the caller.

## The operations the library drives

| Operation | What it does | When it runs |
|---|---|---|
| `boot()` | Single-writer lock + recovery replay of every in-flight record | Process start, always |
| `reconcile(effect_id)` | Adjudicates an ambiguous record by destination query | After ambiguity, or on demand |
| `sweep(adapter_id, window_from, window_to)` | Lists the destination's effects and pairs them with the ledger; orphans become findings | Periodic, per adapter |
| `resolve(finding_id, action, evidence)` | Closes a finding with recorded evidence | Human or policy-driven |
| `status(effect_id)` | Read-only composed view: record, receipts, findings, classification | Whenever you need to look |

## What not to do

- **Do not derive identity from model output.** No key-derivation path reads it — that
  is conformance-tested, and your integration should preserve the property: pass real
  business identifiers in `stable_ids`.
- **Do not retry around the gate.** A denied duplicate is the system working; the deny
  decision cites the blocking execution and its evidence.
- **Do not treat `AMBIGUOUS` as failure.** Discarding an ambiguous record discards
  evidence; the record exists precisely so recovery can adjudicate it.

## Destination support

Today the only qualified destinations are the in-repo reference destinations
(C1/C2/C3 semantics, deterministic, local). Stripe C1 and EasyPost C2 adapter
implementations exist only as never-live-called, synthetic-transport-tested drafts:
they reject production credentials and are not evidence of provider behavior.
Live-sandbox qualification remains human-gated — see the
[adapter development guide](/docs/adapter-development/) for the declaration and
evidence a destination requires.
