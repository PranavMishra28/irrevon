---
title: "Record schemas and API contracts — dispatchable request model, calibrated absence bounds, payload versioning; record schemas deferred to M3"
sourcePath: "docs/decisions/0019-record-schemas-and-api-contracts.md"
sourceSha256: "fa68277b82a554a15dc33eb28ebed558870b991e71baf1313fabc353d3dd1a0c"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0019"
  status: "accepted (ratified in writing by the owner, 2026-07-21)"
  date: "2026-07-21"
  supersedes: "—"
---

## Context

The 2026-07-21 adversarial validity review (critic C1) found a structural blocker in the
shipped contracts: **no public contract carries the destination binding or effect payload an
adapter needs to perform an effect** (finding B1). The shipped intent contract is a closed
six-field object; the design documents nevertheless require the adapter to receive a
validated payload and to know which destination to call. Passing either through a side
channel would violate the trust boundary (master doc §6.3: model-generated content reaches
the deterministic core only via the validated intent contract). Two further findings bear on
the contracts: "confirmed absent" is uncalibrated without destination consistency bounds in
the capability declaration (C1 M3, companion to the AM-9 draft fields), and machine payloads
need a versioning convention (`schema_version`) enforced in the schemas themselves (C1 M13).
Separately, the developer-surface proposal drafted three record schemas (EffectRecord,
DispatchReceipt, ReconciliationFinding); C1 M13 showed those drafts do not enforce their own
contracts, and the ratified state-model correction (amendment AM-18 in the review queue:
DUPLICATE stays n>1; a CONTRADICTED classification is added) changes the classification enum
they would encode.

## Decision

1. **Intent contract gains the dispatchable request model** (fix for C1 B1), preserving the
   identity rule unchanged — identity derives **only** from `stable_ids + effect_type +
   scope` (ADR-001, RFC-001 §1); none of the new members is an identity input, and the
   no-model-output-in-derivation conformance test covers them:
   - `schema_version` (required, `"1"`).
   - `adapter_id` (required): the configured adapter/destination binding for this effect.
   - `parameters` (required, object; may be empty): the effect payload the adapter builds
     the destination request from. Validated against the adapter's per-effect-type
     parameter schema before persistence (adapter-supplied, M4 artifact); the ledger stores
     it with a canonical digest as evidence, never as an identity input.
   - `branch_ref` (optional): workflow branch lineage carrier — gives the commit gate's
     branch check a carrier (absent ⇒ vacuous pass).
   - `event_time` (optional, RFC 3339): upstream business time, evidence only.
2. **Capability declaration gains calibrated consistency bounds** (fix for C1 M3): a
   required `consistency` object with `status_settlement_lag` and `listing_lag` (ISO 8601
   duration, or null when no finite documented/measured bound exists). The engine rule
   (docs/rfc-002-engine-design.md §6): a null bound means confirmed-absence cannot support
   automatic redispatch for that destination — human escalation only. Automatic
   redispatch-on-absence is opt-in per adapter/effect type, never default-on.
3. **`schema_version` convention:** every machine-readable payload (schema instances, SDK
   responses, CLI `--json` output, exports) carries `schema_version`; additive changes do
   not bump it; removals/renames/semantic changes bump it and require an ADR.
4. **The three record schemas are DEFERRED to M3** (T-102), not admitted now. Reasoning:
   (a) the proposal drafts fail their own contract rules (C1 M13 — `schema_version` not
   required, no conditional subject/resolution requirements, receipts missing
   operation/execution identity); (b) the classification enum changed under them (AM-18
   adds CONTRADICTED), so admitting them now would force an immediate second ADR; (c) the
   original deferral rationale in schemas/README.md (no producer/consumer until the ledger
   exists) still holds. Admission criteria, binding on the future ADR: `schema_version`
   required; conditional (`if/then`) requirements tying resolution status to
   `resolved_at`/evidence; `operation_id` on receipts; orphan subjects keyed by
   `(adapter, destination_ref)`; enums generated from the ratified state table
   (docs/rfc-002-engine-design.md §3), never hand-copied.

## Alternatives

- *Side-channel payload delivery (SDK sidecar argument)* — rejected: violates §6.3; the
  trust boundary must be the schema.
- *Admit the three record schemas now* — rejected per item 4; deferral is recorded, not
  silent.
- *Optional `adapter_id`/`parameters`* — rejected: an optional binding reproduces B1 (an
  effect the engine cannot dispatch is unrepresentable as a valid contract instance).

## Consequences

The two shipped schemas change shape (this ADR is the required gate); their example suites
are updated in the same change and must keep passing/failing as labeled. RFC-001 §1's
identity procedure is untouched; RFC-002 consumes the new members. The master-doc §7.3
record-field text now lags the contracts — recorded as proposed amendment AM-17 in the
review queue (master-doc integration pending; contracts govern implementation meanwhile).

## Risks

`parameters` reintroduces model-shaped content into a validated channel — mitigated by
per-adapter parameter schemas, digest-only evidence storage, and the M3 conformance test
that no identity/key derivation path reads it. Adapter parameter schemas do not exist until
M4; until then the stub destination's parameter schema is the only consumer.

## Reopen trigger

The M3 ledger implementation finds the request model insufficient (e.g. multi-step intents
need per-step parameters); or the record-schema admission ADR (M3) discovers a conflict
with the state table; or a second SDK needs a contract member this shape cannot carry.
