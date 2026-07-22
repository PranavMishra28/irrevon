# RFC-001: First vertical slice — Irrevon core

- **Status:** historical record — slice definition and acceptance test remain canonical
  here; state tables are canonical in RFC-002 §3; the identity procedure is canonical in
  ADR-0020.
- **Date:** 2026-07-20 · amended 2026-07-21 (citation fixes; RFC-002 cross-references)
- **Scope:** master doc M3 (state model, intent contract + identity, persist-before-dispatch
  ledger, commit gate, crash-recovery replay, orphan sweep) with the flagship demo (§16,
  item 6) as the acceptance test
- **Reads with [RFC-002](rfc-002-engine-design.md)**, which carries the implementation-ready
  engine mechanics (storage, locked transitions, the canonical state tables, retry/replay
  semantics, calibrated absence). Where this RFC left cells `[OQ]`, RFC-002 §3 decides them.
- **Contains NO code.** Everything here is language-neutral by design and was written while
  ADR-0013 (language) was open; ADR-0013 has since been ratified (Python), but this RFC
  remains implementable in any candidate by construction.

## Summary

The slice is the smallest system that proves the thesis mechanism end-to-end: an intent
contract keyed on stable business identifiers is persisted before dispatch; a deterministic
commit gate guards dispatch; ambiguous outcomes are adjudicated by querying the destination's
authoritative status; and a re-synthesized retry (different model-generated arguments, same
business intent) is rejected as a duplicate with evidence — on a fault schedule that makes the
strongest baseline (B5, durable runtime + native idempotency) produce a duplicate effect.

## Motivation

The residual gap after the strongest baselines lives on C2 destinations, and the master doc's
first public artifact is a reproducible demo of that gap being closed (§1, §16 item 6). This RFC
pins everything about the slice that is cross-cutting, expensive to change later, or required
by the M3 conformance tests (§12.1) — and explicitly defers everything else. Read master doc
§6–§7 first; this document does not restate them.

## Guide-level explanation (the demo, as a story)

An agent asks Irrevon to create an order for `order_id: 9410`. Irrevon validates the intent
contract, persists an INTENDED→PERSISTED record, passes the commit gate, and dispatches to the
C2 destination. The response is lost on cue; the process is killed. On restart, replay finds
the AMBIGUOUS record and — before any new dispatch — queries the destination's status by the
operation reference: the order exists. The record settles SETTLED_COMMITTED with a
CONFIRMED_UNIQUE finding and an evidence bundle. The agent then retries with re-synthesized
arguments (different wording, same `order_id: 9410`); identity derivation maps it to the same
`intent_id`, and the gate rejects it as a duplicate, citing the settled record. The identical
fault script run under the B5 baseline creates a second order, proven by destination
read-back. That contrast is the whole project in one run.

## Reference-level explanation

### 1. Identity: canonicalization and hashing

`intent_id = hash(canonical(stable_ids) ‖ effect_type ‖ scope)` (§7.2). This is the least
reversible decision in the slice — changing it re-keys every ledger record — so the byte-level
procedure is pinned here `[DD]`:

1. **Canonical form:** the tuple is encoded as a JSON object
   `{"effect_type": …, "scope": …, "stable_ids": {…}}` and canonicalized per **RFC 8785
   (JCS)**: lexicographic member ordering, no insignificant whitespace, canonical number and
   string encoding, UTF-8 bytes.
2. **Normalization before canonicalization:** stable-id values are strings, compared and
   hashed exactly as supplied (no case folding — upstream identifiers are opaque); absent
   optional members are omitted, never null (absent ≠ null; null is rejected by the schema).
3. **Hash:** SHA-256 over the canonical UTF-8 bytes; `intent_id` is the lowercase hex digest.
4. **`operation_id` = `intent_id ‖ ":" ‖ step`** where `step` is a zero-based integer assigned
   by the workflow, not the model. Idempotency evidence derives **only** from `operation_id`.
5. **Conformance rule (tested at M3):** no derivation path reads model output. Model-generated
   argument payloads are not inputs to any function in this chain.

Per §12.5 this is invariant-affecting: implementing it requires a short ADR ratifying items
1–4 (JCS + SHA-256 are this RFC's proposal; the ADR is the record of acceptance).

### 2. State-transition matrix (dimension A, exhaustive)

Legal transitions; every pair not listed is illegal and must be rejected (M3 exit test:
exhaustive state-matrix tests, §12.1).

| From \ To | PERSISTED | DISPATCHED | SETTLED_COMMITTED | SETTLED_FAILED | AMBIGUOUS | CANCELLED |
|---|---|---|---|---|---|---|
| INTENDED | durable write | — | — | — | — | branch cancelled pre-persist |
| PERSISTED | — | commit gate allow | — | — | — | cancelled pre-dispatch |
| DISPATCHED | — | — | confirmed receipt | confirmed failure | timeout / lost response / crash | — |
| AMBIGUOUS | — | — | reconciled: effect exists | reconciled: confirmed absent | — | — |

SETTLED_COMMITTED, SETTLED_FAILED, and CANCELLED are terminal.

**Dimension-B attachment rules** (reconciliation classification, §7.1):

- ORPHANED is representable **only as a Finding keyed by `(adapter, destination_ref)`** —
  never as a state of a ledger record (a ledger-keyed machine cannot express a record it
  doesn't have).
- CONFIRMED_UNIQUE, DUPLICATE, and LOST attach only to records that reached DISPATCHED or
  later; records in INTENDED/PERSISTED/CANCELLED are UNRECONCILED by definition.
- The formerly-`[OQ]` cells (e.g. SETTLED_FAILED × DUPLICATE) are now decided: the
  exhaustive attachment matrix — including the CONTRADICTED classification added by
  amendment AM-18 — is canonical in [RFC-002 §3](rfc-002-engine-design.md), and the M3
  matrix tests are generated from it.

**Dimension-C resolution** (per finding): OPEN → COMPENSATED | REDISPATCHED (fresh authority +
new idempotency evidence only) | ACCEPTED_AS_IS | ESCALATED_HUMAN → CLOSED.

### 3. Ledger discipline

Append-only: no UPDATE on settled facts; corrections and state changes are new rows
referencing the prior row. Single writer in the POC; concurrency is per-scope serialization —
one in-flight dispatch per `(scope, effect_type)` via row locking (§7.4 item 3, documented
scaling limit; the crash-safe mechanical form — durable open-attempt rows, locks never held
across wire I/O — is pinned in RFC-002 §5). Physical schema, indexes, and migration tooling are deferred (ADR-0013 and the
storage decision refine them; see [schemas/README.md](../schemas/README.md) for which record
shapes are schema-fied now vs deferred).

### 4. Commit gate: checks and order

Order pinned `[DD]` (cheapest/absolute first; evidence-richest last):

1. **Deny-list** — incident containment (§12.4); a denied effect class aborts immediately.
2. **Authority freshness/binding** — `authority_ref` present, unexpired at gate time, bound to
   this scope; expiry between persist and dispatch → deny, safe abort (§7.4 item 4).
3. **Branch-lineage validity** — the intent's workflow branch has not been cancelled.
4. **Dedup** — no record with the same `intent_id` in DISPATCHED/AMBIGUOUS/SETTLED_COMMITTED;
   a hit denies with the settled record as evidence (this is the re-synthesis defeat).

Every deny writes an evidence record (which check, inputs digested, timestamp). The gate is
deterministic: same ledger state + same contract → same outcome.

### 5. Crash-recovery replay

On restart, before accepting any new work:

1. Scan the ledger for records in DISPATCHED or AMBIGUOUS.
2. For each, run `reconcile(effect_id)` **before any new dispatch of the same
   `operation_id`**.
3. Re-dispatch requires: confirmed-absent at the destination (C2) or in-window idempotent
   replay (C1), **plus** fresh authority. Never re-dispatch on belief (§7.4 item 2).
4. Crash-before-persist is provably effect-free (nothing was dispatched without a durable
   PERSISTED record) — the kill-before-persist test asserts zero external effects (§12.1).

### 6. Orphan sweep

`sweep(adapter, window)`: list destination effects in the window via the adapter's list
query; match each against ledger records by, in order, stamped client reference
(`client_ref_field`), destination_ref recorded on receipts, then declared queryable keys.
Unmatched destination effects emit ORPHANED Findings (dimension B) with the destination
payload digested into the evidence bundle. The sweep is only possible where the capability
declaration says `list_queryable: true` — which is exactly why that field exists (draft
field, amendment AM-9).

### 7. Error taxonomy

| Transport outcome | Meaning | Lifecycle effect |
|---|---|---|
| OK | authoritative success receipt | → SETTLED_COMMITTED |
| FAILED | authoritative, recognized failure semantics from the destination | → SETTLED_FAILED |
| TIMEOUT | no response within deadline | → AMBIGUOUS |
| LOST | connection/process died before response | → AMBIGUOUS |

**Unknown or unrecognized destination errors map to AMBIGUOUS, never FAILED** (§9) — evidence
is never discarded by optimistic classification. Only reconciliation (a status query) or a
human may move AMBIGUOUS to a settled state.

### 8. API operations (language-neutral signatures)

| Operation | Pre | Post |
|---|---|---|
| `registerIntent(contract) → effect_id` | contract validates against the intent-contract schema (≥1 stable id) | INTENDED→PERSISTED record exists; idempotent: same contract returns the same `effect_id` |
| `dispatch(effect_id) → receipt \| AMBIGUOUS` | record is PERSISTED; gate passes | receipt recorded with attempt_no + idempotency evidence; lifecycle per §7 taxonomy |
| `reconcile(effect_id \| scope) → findings` | record(s) DISPATCHED/AMBIGUOUS or settled-for-audit | classification findings recorded; AMBIGUOUS records settled per status query |
| `sweep(adapter, window) → findings` | adapter declares `list_queryable` | ORPHANED findings for unmatched destination effects |
| `resolve(finding, action, evidence)` | finding OPEN; action in dimension C; evidence present | resolution recorded; REDISPATCHED requires fresh authority + new idempotency evidence |
| `status(effect_id) → record view` | record exists | read-only; no state change |

### 9. Test plan (= the M3 rows of §12.1, plus the demo)

1. Property tests over derivation paths: keys derive only from stable identifiers, never
   model output (≥1,000 cases/invariant, §12.2).
2. Kill-before-persist: zero external effects.
3. Exhaustive state-matrix tests over §2 above, including the `[OQ]` cells decided.
4. Architectural test: classifier output cannot reach gate/resolve APIs (ADR-006) — the
   advisory path has no code path to authority.
5. **Acceptance test — the flagship demo script** against the stub destination:
   - Fault 1 (response-lost): dispatch, drop response, crash, restart → replay reconciles to
     SETTLED_COMMITTED + CONFIRMED_UNIQUE; no re-dispatch.
   - Fault 2 (crash-after-effect-before-response): same shape, crash between destination
     effect and response.
   - Fault 3 (semantic re-synthesis): frozen variant retry with different arguments, same
     stable ids → gate rejects duplicate with evidence.
   - **B5 contrast leg:** the identical schedule under stable-op-ID + retry with no honored
     native idempotency produces a duplicate destination effect, proven by read-back.
   The demo graduates from the stub to the real C2 sandbox at M4 (after ADR-0012), and gains
   the C1 null leg (same harness on Stripe shows no advantage) at M4 as well.

### 10. Stub-destination contract (pre-M4 demo runner)

The stand-in C2 destination must implement: `dispatch(op)` creating an effect with a
destination-assigned ref; `status(query)` authoritative by ref or client reference; a
client-reference field (so the slice exercises the same reconcile hooks as a real C2); and
scriptable fault hooks — drop-response-on-cue and effect-created-but-response-lost. It must
be deterministic under a seed.

## Drawbacks

A stub-first demo weakens the "real API" claim until M4; disclosed openly (§8.2 already
scopes what client-side injection can and cannot simulate). Pinning JCS/SHA-256 pre-language
constrains implementations to have a conformant JCS encoder (available in all candidate
ecosystems).

## Rationale and alternatives

The architecture choices this slice implements are already decided and recorded — identity
(ADR-001), persistence (ADR-002), tiers (ADR-003), state (ADR-004), adapters (ADR-005),
authority (ADR-006), compensation (ADR-007) — see master doc §11 via
[decisions/README.md](decisions/README.md). This RFC adds only the byte-level identity
procedure (§1, needs its ADR), the gate order (§4, `[DD]`), and the demo/stub contracts.

## Unresolved questions

- ~~Implementation language and property-test framework~~ — resolved:
  [ADR-0013](decisions/0013-implementation-language.md) accepted 2026-07-21.
- ~~The `[OQ]` cells of the lifecycle × classification matrix (§2)~~ — resolved:
  [RFC-002 §3](rfc-002-engine-design.md) is the canonical matrix.
- The short ADR ratifying the §1 identity procedure (items 1–4) is still owed at
  implementation time (T-101 proposes it; ADR-0013's encoder/hash pins are its inputs).
- C2 sandbox for the M4 graduation — [ADR-0012](decisions/0012-c2-sandbox.md) (OPEN).
- Stripe version pin for the C1 null leg — [ADR-0010](decisions/0010-stripe-api-version.md) (OPEN).
- Bi-temporality (`as_of_time`) stays conditional per ADR-002; the ledger design must not
  preclude it.

## Future possibilities

M4+ real adapters with cited capability declarations; the orphan-sweep demo against a
destination with out-of-band effects; the effect-contract registry (M9).
