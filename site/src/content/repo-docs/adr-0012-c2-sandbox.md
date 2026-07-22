---
title: "Select the C2 sandbox destination for the POC adapter"
sourcePath: "docs/decisions/0012-c2-sandbox.md"
sourceSha256: "cd8d80e987df51327b5af3323320da8e325309288233cd76ac9204fdd96a7dc0"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0012"
  status: "open"
  date: "2026-07-20"
  supersedes: "—"
---

## Context

The POC needs one C2 destination (§5.2); the choice is a §13 blocker and a Stage-B
preregistration precondition. Pre-scaffold verification of the five named C2 candidates
(July 2026) found the C2 classification holds for all five, but sandbox realities differ
sharply and constrain the choice:

| Candidate | Reconcile hooks | Sandbox reality |
|---|---|---|
| Shopify dev store (`orderCreate`) | Orders list/query; client-taggable note attributes/tags/metafields `[VF]`. Re-verified 2026-07-20: `OrderCreateOrderInput.sourceIdentifier` is a purpose-built client reference, searchable via `orders(query:"source_identifier:…")` — strictly stronger than note attributes, which are settable but not server-side searchable `[VF/EI]` | `@idempotent` directive list (Feb 2, 2026; 17 mutations, re-confirmed 2026-07-20) does **not** include orderCreate `[VF]` — affirmative evidence, strongest of the five. Dev stores capped at **5 orders/minute**, confirmed on the mutation page itself — harness must pace `[VF]`. Auth changed Jan 2026: Dev-Dashboard apps only; client-credentials grant; 24h-expiring tokens; app and dev store must share one Dev Dashboard org `[VF]`. Default order read window is 60 days without `read_all_orders` `[VF]` — adequate for sweep windows, recorded as a list bound |
| EasyPost test | Retrieve/list shipments; client-writable `reference` field — strong reconcile hook `[VF]`. Re-verified 2026-07-20: retrieve accepts `reference` in place of `id`, but reference uniqueness is **not enforced** — dedup must handle multi-match `[VF]` | No idempotency documented (full-doc scan; re-confirmed 2026-07-20) `[VF]`. List has no reference filter; `purchased` defaults `true` (sweep overrides); index endpoints capped at 5 rps `[VF]`. Test-mode objects retained **30 days** `[VF]` — bounds all read-back windows |
| Shippo test | Retrieve/list transactions; `metadata` field `[VF]` | No idempotency documented on label purchase `[VF]` |
| Twilio test | Status by SID; list by To/From/DateSent `[VF]` | **No client-reference field** on Messages → orphan matching is heuristic; test credentials likely don't persist queryable records `[OQ — spike required]` |
| Amadeus test | Status by order id `[VF]` | **No list endpoint** in self-service; session-scoped test order IDs → **orphan sweep impossible** in that tier — poor first choice despite headline appeal `[EI]` |

## Decision

**OPEN — decide at the P4 spike (after Stage-A freeze).**
Current leaning `[EI]`: **Shopify dev store primary, EasyPost test fallback** — leaning
strengthened by the 2026-07-20 re-verification (searchable purpose-built client reference;
affirmative non-idempotency evidence re-confirmed; exact setup path documented). Required
spike items before closing: (a) verify Twilio test-mode message persistence (or eliminate
Twilio with evidence); (b) confirm Amadeus list-endpoint absence at the current tier;
(c) confirm Shopify dev-store order query semantics and the 5/min cap's impact on the fault
matrix; (d) check each candidate's ToS for benchmarking use `[OQ — human]`; (e) confirm a
client-credentials token satisfies `orderCreate`'s offline-token requirement `[OQ]`;
(f) observe the `source_identifier` round-trip incl. search-index freshness; (g) observe the
6th-order-per-minute error shape (throttle mapping); (h) EasyPost: duplicate-reference
multi-match behavior and list read-after-write freshness; (i) decide bare-shipment vs
one-call-buy as the C2 effect of record.

## Alternatives

- *Amadeus first (headline travel API)* — disqualified for the POC by the missing list
  endpoint + session-scoped IDs (sweep undetectable ⇒ ORPHANED/LOST unmeasurable).
- *Self-hosted reference destination* — allowed by §13 only with disclosure; weakens the
  "real API" claim for that adapter; last resort. Distinct from the deterministic reference
  destination (docs/rfc-002-engine-design.md §8), which is additive for development and for
  disclosed, separately-reported synthetic benchmark cells — not a substitute for the
  real-sandbox adapter.

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
