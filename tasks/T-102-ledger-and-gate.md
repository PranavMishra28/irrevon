# T-102: Implement the ledger (locked transitions) and commit gate

---
id: T-102
status: done             # completed 2026-07-21
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

- [x] Matrix tests generated from RFC-002 §3: every A pair, A×B cell, and B×C cell matches
      its declared expectation; a meta-test fails on any cell without an expectation.
- [x] Edge case: direct `INSERT` into `effect_transitions` as `detent_app` raises
      `insufficient_privilege`; `ledger_transition` with stale `expected_from` writes nothing.
- [x] Gate order and evidence per RFC-002 §4: every deny and allow writes a decision row;
      dedup deny cites the blocking execution and recorded parameter variants.
- [x] Record schemas admitted per ADR-0019's criteria; `make schemas` green.
- [x] All gates pass (integration via template-database clones on real Postgres 17).

## Required validation

`make check && make py-check py-test py-test-integration`; attach output.

## Documentation updates

Record-schema ADR + decisions/README row; schemas/README deferred section; this file's status.

## Human review triggers — stop and ask if:

- Any RFC-002 §3 cell proves unimplementable or ambiguous (the table is ratified; changing
  it is an amendment, not a local fix).

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.

## Completion record (2026-07-21)

- `make check` → OK; `make py-check` → ruff/mypy-strict/import-linter clean;
  `make py-test` → `55 passed`; `make py-test-integration` → `170 passed` on
  digest-pinned Postgres 17.10 (docker-compose.yml) via template-DB-per-test clones.
- Matrix coverage: dimension A — 56/56 cells (explicit fixture
  `tests/integration/fixtures/lifecycle-matrix.json`, 10 legal / 46 illegal, meta-tests
  enforce completeness + generated-from equality with `detent.statetable` and the SQL
  seed tables); A×B — 35/35 cells + destination-keyed ORPHANED + auto-close of
  CONFIRMED_UNIQUE; B×C — 20/20 cells + status-chain, escalation-reroute,
  first-write-wins, DUPLICATE-never-REDISPATCHED.
- Corrupt-insert tests: direct INSERT into effect_transitions / effect_executions /
  findings / finding_resolutions / lifecycle_edges as `detent_app` →
  `insufficient_privilege`; stale `expected_from` → typed DT002, zero rows written;
  UPDATE/DELETE rejected everywhere by the append-only triggers (even superuser).
- Gate: order pinned (deny_list → authority → branch_lineage → dedup), abort-first with
  `not_reached` statuses recorded; allow AND deny rows written; dedup deny cites blocking
  execution + receipts + parameter variants; §5.2 outcome map incl.
  `retryable_failed` subtype and pending_reconciliation (never re-dispatch on belief).
- Ledger auditor runs after every integration test (autouse post-condition) and is
  self-tested against 10 seeded corruption classes.
- Concurrency: same-stable-ids register race, dispatch race (1 attempt, slot arbitered),
  re-synthesis race collapse — real threads, two connections, no sleeps.
- Record schemas admitted (ADR-0021 proposed) + enum-sync test; migration runner chosen
  (ADR-0022 proposed, fills the ADR-0013 `[OQ]` slot).
