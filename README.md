# Detent

**A preregistered benchmark (DetentBench) and reference reconciliation engine for honest
handling of irreversible AI-agent actions.**

When an LLM agent crosses into an irreversible external action and the outcome is ambiguous —
a lost response, a crash mid-call, or a retry with re-synthesized arguments — duplicate,
orphaned, or lost effects follow. Detent measures how often that happens against real
production API contracts, and how much a deterministic reconciler (identity from stable
business identifiers, persist-before-dispatch, reconcile-by-query) can eliminate or surface.
The project is benchmark-first and scoped to C2 destinations (queryable status, no dependable
native idempotency), with a pre-committed null on C1 and a demonstrated impossibility boundary
on C3.

The full product rationale, architecture, benchmark design, and decision log live in the
[Master Product Document](docs/master-doc.md) — the single authoritative document.

## Status

**Pre-implementation. Docs only. No product code exists yet.**

Phase P0 (scaffold) is complete. The roadmap, gates, and what blocks what are in
[docs/execution-plan.md](docs/execution-plan.md). Items awaiting human decision are in
[docs/review-queue.md](docs/review-queue.md).

## Private repository notice

This repository is **permanently private as a planning repository**. The master document is
preserved byte-identical here and contains personal/planning material unsuitable for
publication. Any public release happens through the public-release gate in the execution plan
(sanitized artifacts, licensing decision, name screen, clearances) — never by flipping this
repository's visibility. See [LICENSING.md](LICENSING.md): all rights reserved, no
contributions accepted.

## Reading order

1. [AGENTS.md](AGENTS.md) — the map: where every concern lives, and the rules for working here.
2. [docs/master-doc.md](docs/master-doc.md) — canonical product intent (read relevant sections
   before any design work).
3. [docs/execution-plan.md](docs/execution-plan.md) — what happens next and in what order.
4. [docs/review-queue.md](docs/review-queue.md) — proposed amendments, open questions, human queue.
5. [docs/decisions/README.md](docs/decisions/README.md) — decision index (settled + open).

## Validation

```sh
make tools   # one-time: install lychee, check-jsonschema, gitleaks, pre-commit (Homebrew)
make check   # links + schemas + secrets + integrity — must pass before any commit
```

`make check` is the only gate. It verifies internal links (offline, deterministic), validates
JSON Schemas and their valid/invalid example suites, scans for secrets, and checks repository
integrity (master-doc hash pin, ADR id uniqueness).
