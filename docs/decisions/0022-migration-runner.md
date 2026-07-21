---
id: ADR-0022
title: Migration runner — minimal in-package plain-SQL runner with a content-hash journal
status: proposed
date: 2026-07-21
supersedes: —
---

## Context

ADR-0013 left the migration-runner tool as an `[OQ]` for the first code milestone, with
the constraint that migrations stay plain, language-neutral `.sql` files (schema
neutrality — a second SDK must be able to reuse them). RFC-002 §2.1 requires plain-SQL
migrations on PostgreSQL 17. The needs are small: apply `migrations/*.sql` in lexical
order, exactly once, refusing silent edits of applied files.

## Decision

Ship a ~60-line runner inside the package (`detent.ledger.db.apply_migrations`): applies
`migrations/*.sql` in lexical filename order, one transaction per file, journaled in
`detent_schema_migrations` with a SHA-256 of the file content. A journaled file whose
content changed is an integrity error, never a silent re-run (append-only discipline:
corrections are new migration files). Migrations are executed by the privileged
migration role; the application role never runs them.

## Alternatives

- Alembic — rejected: ORM-oriented, encourages Python-embedded migrations, breaking the
  language-neutrality constraint.
- Flyway / Liquibase — rejected: JVM toolchain for a task this size.
- golang-migrate / dbmate / goose — capable plain-SQL runners, but each adds an external
  binary to pin and supply-chain-verify for behavior this small; the in-package runner is
  ~60 audited lines with zero new dependencies. The `.sql` files themselves stay runnable
  by any of these tools if the project outgrows the in-package runner.

## Consequences

`detent init`/`doctor` and the test harness share one migration path; the template-DB
test cache keys off the same file hashes. No down-migrations exist (append-only ledger;
rollback is restore-from-backup, consistent with ADR-002).

## Risks

Home-grown runners can miss edge cases (concurrent apply, partial failure) — bounded by:
one-transaction-per-file semantics, the advisory-lock guard in the test harness, and the
tiny surface. If needs grow (checksummed baselines, repeatable migrations), adopt a
dedicated tool and feed it the same files.

## Reopen trigger

A second deployment environment needs concurrent/coordinated migrations; or a migration
requires non-transactional DDL (e.g. CREATE INDEX CONCURRENTLY) the runner cannot express.
