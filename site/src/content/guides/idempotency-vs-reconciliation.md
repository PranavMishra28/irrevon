---
title: "Idempotency keys versus destination reconciliation"
description: "When idempotency keys are sufficient, where their guarantee ends, and why authoritative destination read-back is a different recovery mechanism rather than a replacement."
order: 8
badge: "conceptual"
claims:
  - tiers-table
  - c1-null-precommit
  - reconcile-by-query
---

Idempotency and reconciliation solve related but different problems.
**Idempotency** asks a destination to treat repeated requests carrying the same key
as one operation. **Reconciliation** asks the destination what actually happened
after the caller can no longer prove the outcome.

Irrevon uses native idempotency whenever the destination supports it. It does not
claim an advantage where dependable native idempotency already prevents duplicates.

## When is an idempotency key enough?

An idempotency key is strong when the destination:

- accepts a caller-chosen key for the operation;
- retains it for a documented window;
- returns the first result on replay;
- rejects unsafe parameter drift; and
- states the semantics for failures and concurrent requests.

Irrevon labels that capability C1. For duplicate prevention inside the documented
window, the native destination feature is the primary control. The benchmark
precommits to an expected null: Irrevon should not pretend to improve that duplicate
rate.

Stripe's [official idempotent request documentation](https://docs.stripe.com/api/idempotent_requests)
is an example of why the contract must be version-pinned and read precisely rather
than inferred from the existence of an `Idempotency-Key` header.

## Why can keys still fail in agent workflows?

The caller must reuse the **same** key for the **same** business intent. A model can
regenerate a request after a context reset, change incidental parameters, or invent
a new key. A key derived from request arguments then describes syntax, not business
identity.

Irrevon derives operation identity from stable upstream facts such as an order ID,
approved task ID, or authorization ID. The model can propose parameters, but it does
not define identity or settlement authority.

Keys also have capability boundaries: a provider may ignore the header, retain it
only briefly, apply it to some endpoints, or offer no dependable replay semantics.
A declaration must cite the exact API version and observed contract.

## What does reconciliation add?

For a C2 destination, dependable native idempotency is absent but authoritative
read-back exists. After an ambiguous attempt, reconciliation queries by a stable
reference and classifies the observed external state:

| Question | Idempotency | Reconciliation |
|---|---|---|
| Prevent a same-key replay? | Yes, when the destination honors the contract | Not by itself |
| Resolve a lost response? | Sometimes, by replaying inside the contract | Yes, when authoritative read-back exists |
| Find destination-only effects? | Usually no | A bounded orphan sweep can |
| Prove absence? | Not generally | Only if the destination query semantics support it |
| Work on an opaque C3 destination? | No | No |

Reconciliation is not a universal exactly-once mechanism. It cannot recover
information the destination does not expose.

## What should an integration choose?

Use both controls when available:

1. derive identity from stable business facts;
2. persist before dispatch;
3. send the destination's native idempotency key;
4. record the attempt and response;
5. reconcile ambiguous outcomes against authoritative destination state; and
6. keep unknown outcomes ambiguous.

Read [what happens when an API response is lost](/docs/ambiguous-api-outcomes/) for the
failure sequence, and [adapter development](/docs/adapter-development/) for the
capability declaration contract.
