# T-102: Implement the ledger (locked transitions) and commit gate

---
id: T-102
status: draft
depends_on: [T-101]
invariant: "master doc §7.4 item 1 — no dispatch without a durably persisted intent; RFC-002 §3 state legality"
---

## Objective

The Postgres 17 ledger — plain-SQL migrations, locked transition/execution/resolution
functions, deterministic commit gate — with the RFC-002 §3 matrix tests green.

## Why

RFC-002 §2.3 makes the ledger the sole transition writer (validity-review fix B2); the gate
and every later component depend on it. The record schemas are admitted here (ADR-0019 item 4).

## Context — read these first

- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §2 (storage, locked
  functions), §3 (canonical tables — generate, don't hand-copy), §4 (gate), §13 (locking)
- [docs/decisions/0019-record-schemas-and-api-contracts.md](../docs/decisions/0019-record-schemas-and-api-contracts.md) item 4

## Scope

**Allowed to write:** `migrations/**` (plain SQL), `src/detent/{ledger,gate}/**`,
`tests/**`, the record-schema admission ADR + the three record schemas and example suites
(ADR-0019 criteria), the migration-runner choice for the ADR-0013 `[OQ]` slot, this
file's status.
**Forbidden:** adapters, dispatcher/wire code (T-103), CLI, CI workflows.

## Acceptance criteria

- [ ] Matrix tests generated from RFC-002 §3: every A pair, A×B cell, and B×C cell matches
      its declared expectation; a meta-test fails on any cell without an expectation.
- [ ] Edge case: direct `INSERT` into `effect_transitions` as `detent_app` raises
      `insufficient_privilege`; `ledger_transition` with stale `expected_from` writes nothing.
- [ ] Gate order and evidence per RFC-002 §4: every deny and allow writes a decision row;
      dedup deny cites the blocking execution and recorded parameter variants.
- [ ] Record schemas admitted per ADR-0019's criteria; `make schemas` green.
- [ ] All gates pass (integration via template-database clones on real Postgres 17).

## Required validation

`make check && make py-check py-test py-test-integration`; attach output.

## Documentation updates

Record-schema ADR + decisions/README row; schemas/README deferred section; this file's status.

## Human review triggers — stop and ask if:

- Any RFC-002 §3 cell proves unimplementable or ambiguous (the table is ratified; changing
  it is an amendment, not a local fix).

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.
