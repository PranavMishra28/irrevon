# Detent

**DetentBench, a fault-injection benchmark for irreversible AI-agent actions, and Detent,
its reference reconciliation engine.** The benchmark plan is written for preregistration
and is currently a draft; no section is frozen
([docs/benchmark-preregistration.md](docs/benchmark-preregistration.md) §0).

When an LLM agent crosses into an irreversible external action and the outcome is ambiguous —
a lost response, a crash mid-call, or a retry with re-synthesized arguments — duplicate,
orphaned, or lost effects follow. DetentBench is designed to measure how often that happens
against real production API contracts, and how much of it a deterministic reconciler
(identity from stable business identifiers, persist-before-dispatch, reconcile-by-query)
can eliminate or surface. The project is benchmark-first and scoped to C2 destinations
(queryable status, no dependable native idempotency), with a pre-committed null on C1 and a
demonstrated impossibility boundary on C3.

The full product rationale, architecture, benchmark design, and decision log live in the
[Master Product Document](docs/master-doc.md) — the single authoritative document.

## Status

**Pre-implementation. Docs and contracts only. No product code exists yet.**

The engine design is implementation-ready ([docs/rfc-002-engine-design.md](docs/rfc-002-engine-design.md));
the language/stack decision is closed (ADR-0013, Python); implementation remains gated by
the execution plan's P1 gate. The roadmap, gates, and what blocks what are in
[docs/execution-plan.md](docs/execution-plan.md). Items awaiting human decision are in
[docs/review-queue.md](docs/review-queue.md).

## Repository status and licensing

This repository is public (owner decision, 2026-07-21) but **not yet released software**:
there is no LICENSE file, all rights are reserved, and **no contributions are accepted**
while the licensing decision ([ADR-0014](docs/decisions/0014-licensing.md)) is open. Do not
build on this repository yet. Packaged releases, published artifacts, and the contribution
policy arrive only through the public-release gate in
[docs/execution-plan.md](docs/execution-plan.md). See [LICENSING.md](LICENSING.md).

## Reading order

1. [AGENTS.md](AGENTS.md) — the map: where every concern lives, and the rules for working here.
2. [docs/master-doc.md](docs/master-doc.md) — canonical product intent (read relevant sections
   before any design work).
3. [docs/rfc-001-first-slice.md](docs/rfc-001-first-slice.md) and
   [docs/rfc-002-engine-design.md](docs/rfc-002-engine-design.md) — the first slice and its
   engine mechanics.
4. [docs/execution-plan.md](docs/execution-plan.md) — what happens next and in what order.
5. [docs/review-queue.md](docs/review-queue.md) — amendments, open questions, human queue.
6. [docs/decisions/README.md](docs/decisions/README.md) — decision index (settled + open).

## Validation

```sh
make tools   # one-time: install lychee, check-jsonschema, gitleaks, pre-commit (Homebrew),
             # then verify installed versions against the tested pins
make check   # links + schemas + secrets + integrity — must pass before any commit
```

`make check` is the required local gate (pre-commit additionally runs the secret scan on
every commit). It verifies internal links (offline, deterministic), validates JSON Schemas
and their valid/invalid example suites, scans for secrets, and checks repository integrity
(master-doc hash pin, ADR id uniqueness).
