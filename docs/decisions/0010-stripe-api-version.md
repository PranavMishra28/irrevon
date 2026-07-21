---
id: ADR-0010
title: Pin the Stripe API version and idempotency semantics for the C1 adapter
status: open
date: 2026-07-20
supersedes: —
---

## Context

Master doc §11 records ADR-010 as OPEN: pin the Stripe API version after an M4 spike, before
contract tests, because the choice changes the C1 contract and B4/B5 expectations. The two
candidate semantics differ materially `[VF]`:

- **v1:** `Idempotency-Key` on POST only; results **including errors (even 500s)** cached and
  replayed; keys pruned after **at least 24 hours**; same key + different params → error.
- **v2:** POST and DELETE; **30-day** window scoped to account/sandbox + API; failed requests
  are **re-executed without side effects** rather than replaying the cached error.

**Scope caveat that narrows this decision** (proposed amendment AM-5 in
[../review-queue.md](../review-queue.md)): v2 semantics apply only to `/v2`-namespace APIs.
Core payments objects (PaymentIntents, Charges) remain in the v1 namespace, so a Stripe
test-mode C1 adapter exercising payment-like effects operates under **v1 semantics regardless
of preference** `[EI]`. A community-confirmed sharp edge supports the project thesis: on a
5xx under v1, the original request may still have had side effects, and Stripe's guidance is
to reconcile via webhooks/events — even the flagship C1 destination pushes
reconcile-by-query for the ambiguous tail `[VF]`.

## Decision

**OPEN — decide at the P5 spike (before contract tests, per §11).**
Current leaning `[EI]`: pin **v1 semantics (24h window, cached-error replay)** for the
endpoints the adapter touches, and document v2 as inapplicable unless the adapter uses `/v2`
endpoints. The spike must (a) enumerate the exact endpoints the C1 adapter calls, (b) confirm
their namespace, and (c) record the replay-window and error-replay behavior observed in test
mode into the capability declaration.

## Alternatives

- *Assume one version silently* — rejected by §11: the choice changes B4/B5 baseline
  expectations and must be explicit and cited.
- *Target /v2 endpoints to get the friendlier 30-day retry semantics* — premature: payments
  objects are not there; revisit only if the adapter's effect set changes.

## Consequences

The capability declaration for Stripe pins `api_version` and the idempotency window with
citations; B4/B5 operationalization in the Stage-B preregistration inherits the pinned
semantics.

## Risks

Stripe migrates payments objects to /v2 between now and M4 — the spike must re-verify
namespaces at execution time rather than trusting this record.

## Reopen trigger

Adapter's endpoint set changes namespace; or Stripe changes documented replay semantics
(contract drift → declaration update + retest + deviation ADR per §7.6).
