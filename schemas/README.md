# Schemas — machine-readable contracts

JSON Schema **2020-12**, one resource per file, validated by `make schemas` (metaschema check;
`examples/<name>/valid-*.json` must pass; `examples/<name>/invalid-*.json` must fail — the
invalid suite is the executable form of the Intent Registrar's rejection rules). Tooling
rationale: [ADR-0015](../docs/decisions/0015-schema-validation-tooling.md). Shape changes
require an ADR (`.cursor/rules/contracts.mdc`).

`$id` values use the placeholder host `detent.invalid` — identifiers, not locators; final
URIs are set after the name screen closes (master doc §13).

## Shipped now (2)

| Schema | Why now |
|---|---|
| [intent-contract.schema.json](intent-contract.schema.json) | THE trust boundary (master doc §6.3): nothing model-generated crosses into the deterministic core except via this validated contract. Consumed by the first implementation task. |
| [capability-declaration.schema.json](capability-declaration.schema.json) | The exchange format for destination capabilities (§7.3/§7.5/§7.6); pins the two draft fields the C2 research surfaced (`client_ref_field`, `list_queryable` — amendment AM-9) while the evidence is fresh. |

Both carry `$comment: draft` — they are pre-implementation contracts, refined at ratification
of the amendments they embed.

## Deferred (3), and why

**EffectRecord, DispatchReceipt, ReconciliationFinding** are internal ledger shapes, frozen
verbatim in master doc §7.3. They are deferred to M3 because: (a) they have no producer or
consumer yet — invalid-example suites for records nothing emits would be theater; (b) the
language/storage decision (ADR-0013, and the ledger DDL that follows) will refine how the
exchange shape maps to storage. Encode them when the ledger code exists to be validated
against them.

Also deferred: adapter interface (language-shaped, ADR-0013), benchmark run-manifest/result
records, fault-schedule and re-synthesis-variant formats (all Stage-B preregistration
artifacts), evidence-bundle format (depends on the redaction pipeline, §9).
