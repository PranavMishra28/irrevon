---
id: ADR-0021
title: Admit the three record schemas (EffectRecord, DispatchReceipt, ReconciliationFinding) at M3 per the ADR-0019 criteria
status: proposed
date: 2026-07-21
supersedes: —
---

## Context

ADR-0019 item 4 deferred the three record schemas to M3 (T-102) and recorded binding
admission criteria: `schema_version` required; conditional (`if/then`) requirements tying
resolution status to `resolved_at`/evidence; `operation_id` on receipts; orphan subjects
keyed by `(adapter, destination_ref)`; enums generated from the ratified state table
(RFC-002 §3), never hand-copied. T-102 implements the ledger, so the shapes now have a
producer (the ledger read surface / Q1–Q2 payloads, RFC-002 §9) and consumers (the
workbench contract, `detent inspect --json`).

## Decision

Admit `schemas/effect-record.schema.json`, `schemas/dispatch-receipt.schema.json`, and
`schemas/reconciliation-finding.schema.json` with example suites, satisfying every
ADR-0019 criterion:

- `schema_version` (const `"1"`) required on all three.
- Receipts carry `operation_id`, `attempt_no`, `kind`, `adapter_id`,
  `declaration_digest` (execution identity + C1 M17 declaration versioning), and mirror
  the ledger CHECK `(transport_outcome = FAILED) = (failure_kind present)` as `if/then`.
- Findings: strict `oneOf` subject (ledger-keyed vs destination-keyed);
  `ORPHANED ⇔ destination-keyed` and `DUPLICATE ⇒ excess_effect_count ≥ 1` as `if/then`;
  resolution status beyond OPEN requires `resolved_at` + evidence digest; evidence is
  exposed digest-only until the redaction pipeline exists (RFC-002 §9 Q2).
- Enum drift is mechanically prevented: `tests/schemas/test_enum_sync.py` asserts every
  schema enum equals `detent.statetable` (the single in-code encoding of RFC-002 §3,
  itself cross-checked against the SQL seed tables by the integration suite).
- UNRECONCILED stays absence-of-findings (RFC-002 §3.2 decided the former RQ-3).

Deviations from the scratch proposals (dx-api §5), recorded: `event_time` keeps the
ADR-0019 meaning (optional upstream business time) and the state-change timestamp is a
separate required `lifecycle_at`; receipt/finding id prefixes are pinned with the ledger
bigint zero-padded as the suffix (ULID deferred — no coordination need in a single-writer
POC).

## Alternatives

- Keep deferring — rejected: T-102 creates the producer; deferral rationale expired.
- Hand-copied enums — rejected by ADR-0019 (drift is the failure mode AM-18 exposed).

## Consequences

`make schemas` now gates five schemas; the workbench (ADR-0016 workstream) can consume
Q1/Q2 payloads without a translation layer. Any shape change requires an ADR.

## Risks

The exchange shapes may prove too narrow once real adapters land (M4); additive optional
fields do not bump `schema_version`, so the risk is bounded.

## Reopen trigger

M4 adapter work needs a member these shapes cannot carry; or the benchmark harness (M5)
needs a run-record composition these shapes contradict.
