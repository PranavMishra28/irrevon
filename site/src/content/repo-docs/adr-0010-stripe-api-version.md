---
title: "Pin the Stripe API version and idempotency semantics for the C1 adapter"
sourcePath: "docs/decisions/0010-stripe-api-version.md"
sourceSha256: "dd77254e12e7cb63c9e2b72187bea35f400e818147e7eeb9b3c3fbe5c0a2bfee"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0010"
  status: "open"
  date: "2026-07-20"
  supersedes: "—"
---

## Context

Master doc §11 records ADR-010 as OPEN: pin the Stripe API version after an M4 spike, before
contract tests, because the choice changes the C1 contract and B4/B5 expectations. The two
candidate semantics differ materially `[VF]`:

- **v1:** `Idempotency-Key` on POST only; results **including errors (even 500s)** cached and
  replayed; keys pruned after **at least 24 hours**; same key + different params → error.
- **v2:** POST and DELETE; **30-day** window scoped to account/sandbox + API; failed requests
  are **re-executed without side effects** rather than replaying the cached error.

**Scope caveat that narrows this decision** (amendment AM-5 in
[../review-queue.md](../review-queue.md)): v2 semantics apply only to `/v2`-namespace APIs.
Core payments objects (PaymentIntents, Charges) remain in the v1 namespace, so a Stripe
test-mode C1 adapter exercising payment-like effects operates under **v1 semantics regardless
of preference** `[EI]`.

**Decision-ready evidence (verified against current official docs, 2026-07-20):** Stripe's
own low-level error documentation states the sharp edge directly: idempotency caches 500
responses, the original request "may have produced side effects", results should be treated
as indeterminate, Stripe performs internal reconciliation and fires webhooks for objects
created during it, and the recommended client cross-reference is a local identifier in
`metadata` (docs.stripe.com/error-low-level) `[VF]` — the flagship C1 destination prescribes
reconcile-by-query plus client-reference stamping for the ambiguous tail. Namespace
re-verified 2026-07-20: PaymentIntents/Charges/Refunds remain `/v1`; `/v2` covers
core/accounts, money-management, event destinations. A Stripe maintainer states publicly
there are no short-term plans to migrate payments to v2 (stripe-java#2153) `[EI]`.
Additional v1 nuances for the declaration: results are cached only once endpoint execution
begins (429/validation errors are not cached; rate limiters run before the idempotency
layer — a 429 is safely side-effect-free `[VF]`); concurrent same-key requests → 409, not
cached; replays are flagged `Idempotent-Replayed: true`. Reconcile hooks: `GET
/v1/payment_intents` (list) is immediately consistent and windowable by `created`;
Search-by-metadata is eventually consistent (typically <1 min) with a 20 read-ops/s cap —
reconcile uses list/retrieve, the orphan sweep may use search with a freshness allowance
`[VF]`.

## Decision

**OPEN — decide at the P5 spike (before contract tests, per §11).**
Current leaning `[EI]`: pin **v1 semantics (≥24h window — keys pruned after at least 24
hours; cached-error replay incl. 500s; parameter-mismatch error)** for all endpoints the C1
adapter touches, and pin the exact dated API version current at the spike via
`Stripe-Version`. Document v2 (30-day window, retry-without-side-effects, POST+DELETE) as
inapplicable while the endpoint set is `/v1`-only. Spike checklist: (a) enumerate the exact
endpoints (expected: `POST /v1/payment_intents`, `POST /v1/payment_intents/:id/confirm`,
`GET /v1/payment_intents/:id`, `GET /v1/payment_intents` list, `POST /v1/refunds`) and
re-check their namespace; (b) observe replay incl. `Idempotent-Replayed: true`; (c) observe
cached-error replay on an induced 4xx; (d) observe 409 concurrent-key behavior; (e) measure
search-by-metadata freshness (bounds the sweep); (f) confirm sandbox rate-limit headroom vs
the harness schedule.

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
namespaces at execution time rather than trusting this record. Stripe test-data retention
for payments objects is undocumented `[OQ]`; benchmark read-backs must not assume
indefinite persistence.

## Reopen trigger

Adapter's endpoint set changes namespace; or Stripe changes documented replay semantics
(contract drift → declaration update + retest + deviation ADR per §7.6).
