---
title: "What happens when an API commits but its response is lost?"
description: "A direct guide to ambiguous API outcomes: why a timeout is not proof of failure, what evidence is safe to use, and when a retry can create a duplicate external effect."
order: 7
badge: "conceptual"
claims:
  - problem-ambiguous-outcome
  - reconcile-by-query
  - no-exactly-once
---

An API timeout says that the caller did not receive a conclusive response. It does
**not** say whether the destination committed the requested effect. If a payment,
booking, shipment, or message may already exist, the honest state is
`AMBIGUOUS`: neither success nor failure is yet proven.

## Why is a timeout not proof of failure?

The request and response cross separate network paths. The destination can commit
the effect and then lose the response because the connection breaks, a proxy times
out, or the client process crashes. From the caller's perspective, that history is
indistinguishable from a request that never arrived unless the destination exposes
evidence that resolves it.

```text
caller ── request ──> destination
                      commits effect
caller <── response X  connection lost
```

Classifying that outcome as `FAILED` discards uncertainty. Retrying immediately can
create a second effect. Assuming success can suppress a legitimate retry when the
first request truly did not commit.

## What is the safe recovery sequence?

1. Persist the business intent and operation identity before dispatch.
2. Record the bounded attempt and its transport outcome.
3. Preserve `AMBIGUOUS` after a timeout, lost response, or crash.
4. Query the destination by a stable operation or destination reference.
5. Settle committed or absent only when the returned evidence supports it.
6. Re-dispatch only under policy after confirmed absence and fresh authority.
7. Escalate when the destination cannot answer.

The destination's state is authoritative for the external effect. Local logs prove
what the caller attempted; they do not prove what the destination committed.

## Example: a retry after a committed response-loss

Suppose an agent creates shipment `approved_task_id=task-42`. The carrier commits
it, but the response never reaches the agent. The model later generates slightly
different arguments and tries again.

An argument hash may treat the second request as new. Irrevon instead derives the
same operation identity from stable upstream business facts, finds the ambiguous
record, and queries the destination. If read-back proves the shipment exists, the
ledger records the evidence and denies the duplicate dispatch.

This is a mechanism example, not a live-provider result. The repository's recorded
demo uses a deterministic synthetic C2 destination; provider adapters have not yet
been live-called.

## What if the destination cannot be queried?

If the destination offers neither dependable idempotency nor authoritative
read-back, the caller cannot manufacture certainty. Irrevon calls that C3, the
opaque capability tier. The correct outcome remains unresolved or goes to human
review; the system does not relabel ignorance as failure.

## What should an API integration record?

Record stable business identifiers, the derived operation identity, attempt number,
idempotency evidence, transport outcome, destination reference when available, and a
digest of the evidence used for settlement. Avoid treating raw model wording as
identity, and minimize personal or confidential payload data.

Next, compare [idempotency keys with destination reconciliation](/docs/idempotency-vs-reconciliation/)
or follow the [integration guide](/docs/integration/).
