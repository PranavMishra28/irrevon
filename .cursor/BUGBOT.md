# Irrevon — Bugbot review guide

Irrevon is a reconciliation engine + preregistered benchmark (IrrevonBench) for irreversible
AI-agent actions. The costliest bugs here are not crashes — they are silent violations of
identity, durability, and benchmark-integrity invariants. Review for these first.
Canonical sources: docs/master-doc.md §6–§9, §12; docs/rfc-001-first-slice.md; AGENTS.md.

## Identity derivation must be pure (highest priority)

- `intent_id` and `operation_id` must be derived ONLY from caller-supplied intent fields via
  the frozen procedure (RFC 8785/JCS canonicalization → SHA-256). Flag ANY code path where
  model/LLM output, timestamps, random values, retry counters, or environment data flow into
  identity derivation. Same intent must yield the same id on every retry, forever.
- Flag any second implementation of canonicalization or hashing (drift risk): there must be
  exactly one encoder path, version-pinned, with cross-implementation conformance vectors.

## Persistence and transaction safety

- Persist-before-dispatch: an operation must be durably recorded (committed, not just
  buffered) BEFORE any external side effect is attempted. Flag dispatch calls that precede
  the commit, or that share a transaction with it such that rollback could orphan a
  side effect.
- Flag transactions that hold locks across network I/O, missing `SELECT ... FOR UPDATE`
  where row ownership matters, and any read-modify-write on ledger state outside a
  transaction.

## Append-only ledger discipline

- Ledger tables are append-only: flag UPDATE/DELETE on ledger rows, soft-delete flags, or
  migrations that rewrite/drop historical rows. State changes are new records, never edits.

## Benchmark integrity (never help a metric win)

- Flag any change that weakens baselines, reduces property-test case counts (≥1,000
  cases/invariant is spec), relaxes assertions, adds skips/xfails, or edits anything in a
  FROZEN preregistration section. These are potential integrity violations even when the
  diff looks like "fixing a flaky test". INVALID-run handling must never become a post-hoc
  exclusion lever.

## Workflow security (.github/**)

- Every `uses:` must be pinned to a full 40-char commit SHA with a version comment.
- Every workflow: top-level permissions of at most `contents: read`, explicit per-job
  grants for anything beyond; `persist-credentials: false` on checkouts; no
  `pull_request_target`; no interpolation of untrusted event text (issue/PR bodies, branch
  names) into `run:` — env indirection only.

## Contracts

- Any change to `schemas/*.schema.json` shape/enums/required fields without a referenced ADR
  is a finding. Examples must keep passing/failing as labeled.

## Note to humans

Bugbot is advisory here. Its check reports findings as `neutral` and MUST NOT be the sole
required gate: `make check`, the test suite, and human review remain the enforcing controls.
