---
title: "Schemas — machine-readable contracts"
description: "The machine-readable contract map: five shipped JSON Schemas, their example suites, and what is deliberately deferred."
sourcePath: "schemas/README.md"
sourceSha256: "11530ff6a51e1b044c34b0a8147a45701d05e1d934e0c8f43309f4cecbbeb961"
syncedAt: "2026-07-22"
section: "Contracts"
renderTitle: false
---

# Schemas — machine-readable contracts

JSON Schema **2020-12**, one resource per file, validated by `make schemas` (metaschema check;
`examples/<name>/valid-*.json` must pass; `examples/<name>/invalid-*.json` must fail — the
invalid suite is the executable form of the Intent Registrar's rejection rules). Tooling
rationale: [ADR-0015](../docs/decisions/0015-schema-validation-tooling.md). Shape changes
require an ADR (`.cursor/rules/contracts.mdc`); the current shapes were set by
[ADR-0019](../docs/decisions/0019-record-schemas-and-api-contracts.md) (2026-07-21).

`$id` values use the host `irrevon.dev` — identifiers, not locators, and still a
**placeholder**: the name is decided (ADR-0023) but the domain is not yet purchased
(owner spend decision, launch checklist). URIs become locators only after that purchase.

## Shipped now (5)

| Schema | Why now |
|---|---|
| [intent-contract.schema.json](intent-contract.schema.json) | The trust boundary (master doc §6.3): nothing model-generated crosses into the deterministic core except via this validated contract. ADR-0019 added the dispatchable request model (`schema_version`, `adapter_id`, `parameters`, `branch_ref`, `event_time`); identity still derives only from `stable_ids + effect_type + scope`. Consumed by the first implementation task (T-101). |
| [capability-declaration.schema.json](capability-declaration.schema.json) | The exchange format for destination capabilities (§7.3/§7.5/§7.6); carries the AM-9 fields (`client_ref_field`, `list_queryable` — ratified 2026-07-21) and the ADR-0019 `consistency` bounds that calibrate confirmed-absence (RFC-002 §6). |
| [effect-record.schema.json](effect-record.schema.json) | Admitted at M3 (T-102) by [ADR-0021](../docs/decisions/0021-record-schemas-admission.md) (proposed) per the ADR-0019 item-4 criteria — the ledger now produces this view (Q1 item core, RFC-002 §9). |
| [dispatch-receipt.schema.json](dispatch-receipt.schema.json) | Same admission; carries execution identity (`operation_id`) and mirrors the ledger's transport-outcome/failure-kind coupling as `if/then`. |
| [reconciliation-finding.schema.json](reconciliation-finding.schema.json) | Same admission; strict `oneOf` subject (destination-keyed ORPHANED per master doc §7.1), AM-18 classification enum (DUPLICATE n>1 + CONTRADICTED), digest-only evidence until the redaction pipeline exists. |

Record-schema enums are **generated from the ratified state table** (RFC-002 §3 via
`src/irrevon/statetable.py`) and mechanically checked by `tests/schemas/test_enum_sync.py`
plus the integration seed-table cross-checks — never hand-copied (ADR-0019 item 4).

## Deferred, and why

Adapter interface and per-effect-type parameter schemas (M4, ADR-0019),
benchmark run-manifest/result records, fault-schedule and re-synthesis-variant formats (all
Stage-B preregistration artifacts), evidence-bundle format (depends on the redaction
pipeline, §9).
