---
id: ADR-0012
title: Select the C2 sandbox destination for the POC adapter
status: open
date: 2026-07-20
supersedes: —
---

## Context

The POC needs one C2 destination (§5.2); the choice is a §13 blocker and a Stage-B
preregistration precondition. Pre-scaffold verification of the five named C2 candidates
(July 2026) found the C2 classification holds for all five, but sandbox realities differ
sharply and constrain the choice:

| Candidate | Reconcile hooks | Sandbox reality |
|---|---|---|
| Shopify dev store (`orderCreate`) | Orders list/query; client-taggable note attributes/tags/metafields `[VF]` | `@idempotent` directive list (Feb 2, 2026) does **not** include orderCreate `[VF]` — affirmative evidence, strongest of the five. Dev stores capped at **5 orders/minute** — harness must pace `[VF]` |
| EasyPost test | Retrieve/list shipments; client-writable `reference` field — strong reconcile hook `[VF]` | No idempotency documented (full-doc scan) `[VF]` |
| Shippo test | Retrieve/list transactions; `metadata` field `[VF]` | No idempotency documented on label purchase `[VF]` |
| Twilio test | Status by SID; list by To/From/DateSent `[VF]` | **No client-reference field** on Messages → orphan matching is heuristic; test credentials likely don't persist queryable records `[OQ — spike required]` |
| Amadeus test | Status by order id `[VF]` | **No list endpoint** in self-service; session-scoped test order IDs → **orphan sweep impossible** in that tier — poor first choice despite headline appeal `[EI]` |

## Decision

**OPEN — decide at the P4 spike (after Stage-A freeze).**
Current leaning `[EI]`: **Shopify dev store primary, EasyPost test fallback.** Required spike
items before closing: (a) verify Twilio test-mode message persistence (or eliminate Twilio
with evidence); (b) confirm Amadeus list-endpoint absence at the current tier; (c) confirm
Shopify dev-store order query semantics and the 5/min cap's impact on the fault matrix;
(d) check each candidate's ToS for benchmarking use.

## Alternatives

- *Amadeus first (headline travel API)* — disqualified for the POC by the missing list
  endpoint + session-scoped IDs (sweep undetectable ⇒ ORPHANED/LOST unmeasurable).
- *Self-hosted reference destination* — allowed by §13 only with disclosure; weakens the
  "real API" claim for that adapter; last resort.

## Consequences

The chosen destination's capability declaration (with `client_ref_field` and
`list_queryable`) becomes the schema example of record; Stage-B preregistration names the
adapter; the RFC-001 demo graduates from stub to this sandbox at M4.

## Risks

Shopify's `@idempotent` directive list is expanding — if orderCreate gains native idempotency
the destination migrates C2→C1 and the wedge narrows there (tracked quarterly, AM-11).

## Reopen trigger

Chosen destination changes idempotency/query semantics (contract drift, §7.6); or the spike
falsifies a leaning assumption above.
