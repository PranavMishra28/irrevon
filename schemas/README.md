# Schemas — machine-readable contracts

JSON Schema **2020-12**, one resource per file, validated by `make schemas` (metaschema check;
`examples/<name>/valid-*.json` must pass; `examples/<name>/invalid-*.json` must fail — the
invalid suite is the executable form of the Intent Registrar's rejection rules). Tooling
rationale: [ADR-0015](../docs/decisions/0015-schema-validation-tooling.md). Shape changes
require an ADR (`.cursor/rules/contracts.mdc`); the current shapes were set by
[ADR-0019](../docs/decisions/0019-record-schemas-and-api-contracts.md) (2026-07-21).

`$id` values use the placeholder host `detent.invalid` — identifiers, not locators; final
URIs are set after the name screen closes (master doc §13).

## Shipped now (2)

| Schema | Why now |
|---|---|
| [intent-contract.schema.json](intent-contract.schema.json) | The trust boundary (master doc §6.3): nothing model-generated crosses into the deterministic core except via this validated contract. ADR-0019 added the dispatchable request model (`schema_version`, `adapter_id`, `parameters`, `branch_ref`, `event_time`); identity still derives only from `stable_ids + effect_type + scope`. Consumed by the first implementation task (T-101). |
| [capability-declaration.schema.json](capability-declaration.schema.json) | The exchange format for destination capabilities (§7.3/§7.5/§7.6); carries the AM-9 fields (`client_ref_field`, `list_queryable` — ratified 2026-07-21) and the ADR-0019 `consistency` bounds that calibrate confirmed-absence (RFC-002 §6). |

## Deferred (3), and why

**EffectRecord, DispatchReceipt, ReconciliationFinding** are internal ledger shapes. Their
deferral to M3 (T-102) was re-examined and re-affirmed in ADR-0019 item 4: (a) the drafted
proposals did not enforce their own contracts (missing required `schema_version`, missing
conditional subject/resolution requirements, receipts without operation identity); (b) the
ratified state-model correction (amendment AM-18: DUPLICATE stays n>1; CONTRADICTED added)
changes the classification enum they would encode; (c) they still have no producer or
consumer until the ledger exists. ADR-0019 records the binding admission criteria; the
enums must be generated from the ratified state table (RFC-002 §3,
`docs/rfc-002-engine-design.md`), never hand-copied.

Also deferred: adapter interface and per-effect-type parameter schemas (M4, ADR-0019),
benchmark run-manifest/result records, fault-schedule and re-synthesis-variant formats (all
Stage-B preregistration artifacts), evidence-bundle format (depends on the redaction
pipeline, §9).
