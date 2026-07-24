---
title: "Durable workflows, transactional outbox, sagas, and reconciliation"
description: "A boundary-focused comparison of durable execution, transactional outbox, sagas, idempotency, and Irrevon's destination-authoritative reconciliation."
order: 9
badge: "conceptual"
claims:
  - prior-art-credited
  - persist-before-dispatch
  - compensation-not-rollback
  - novelty-boundary
---

Durable workflows, transactional outboxes, sagas, idempotency, and reconciliation
are complementary patterns. They become confusing when a guarantee about **local
state** is described as a guarantee about a separately administered external
destination.

Irrevon's narrow role is to preserve and adjudicate uncertainty at that boundary.
It does not replace a workflow engine, message broker, or provider-native
idempotency.

## What does each pattern control?

| Pattern | Primary boundary | What it gives you | What remains |
|---|---|---|---|
| Durable workflow | Workflow history and retries | Crash-resumable control flow | The external API may have committed before a response was lost |
| Transactional outbox | Local database transaction to dispatch queue | Persist-before-dispatch for local intent | Delivery and destination outcome still need adjudication |
| Idempotency key | Destination replay contract | Duplicate prevention for the same honored key | Key reuse, retention window, unsupported endpoints, and read-back |
| Saga | Multi-step business process | Explicit forward compensations | Compensation is another fallible effect, not rollback |
| Reconciliation | Internal record versus external state | Evidence-backed classification of committed, absent, duplicate, lost, or orphaned effects | Opaque destinations remain unknowable |

## Is Irrevon a workflow engine?

No. A durable workflow engine decides when activities run and how their histories
resume. Irrevon is a reference reconciliation layer at the tool-call boundary. A
workflow can issue a stable operation ID into Irrevon, and Irrevon can persist,
dispatch through a capability-declared adapter, and reconcile ambiguity before a
later attempt is allowed.

Temporal's [retry policy documentation](https://docs.temporal.io/encyclopedia/retry-policies)
correctly emphasizes that activities must account for failure and retry behavior.
Irrevon's benchmark includes a real durable-runtime comparator as planned Stage-B
work; the current recorded B5 leg is a disclosed developmental file-journal
stand-in, not evidence about Temporal.

## Is persist-before-dispatch just an outbox?

It uses the outbox discipline: store the intent durably before crossing the
external boundary. That proves a crash before persistence produced no dispatched
effect and leaves a recovery record after persistence.

An outbox does not by itself prove whether a remote destination committed a request
whose response was lost. The destination query and its capability contract close
that second half when possible.

## Does a saga roll back an irreversible effect?

No. A refund, cancellation fee, reversal message, or replacement shipment is a new
external effect. It can fail independently and must have its own identity,
authority, evidence, and recovery path. Calling that “rollback” hides the
additional real-world history.

## When do these patterns compose?

A production-shaped composition can use:

1. a durable workflow for process history;
2. a local transaction and outbox for intent persistence;
3. stable upstream identifiers for operation identity;
4. provider-native idempotency when supported;
5. destination reconciliation after ambiguous outcomes; and
6. sagas for explicit, measured compensation when policy requires it.

The strongest conventional composition is an important benchmark comparator.
IrrevonBench is explicitly designed so that if this comparator matches the
reference engine on C2 destinations, the project is declared unnecessary and
reframed as a teaching artifact.

See the [architecture guide](/docs/architecture/), the
[idempotency comparison](/docs/idempotency-vs-reconciliation/), and the
[prior-art survey](/research/prior-art/).
