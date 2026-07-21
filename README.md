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

**First slice implemented (M3 core): identity + ledger + gate + dispatcher +
reconciliation + recovery + sweep + the flagship demo**, per
[docs/rfc-002-engine-design.md](docs/rfc-002-engine-design.md) (tasks T-101–T-104).
Real destination adapters (M4), the benchmark harness (M5+), and any packaged release
remain gated by the execution plan. The roadmap, gates, and what blocks what are in
[docs/execution-plan.md](docs/execution-plan.md). Items awaiting human decision are in
[docs/review-queue.md](docs/review-queue.md).

## Quickstart — run the flagship demo

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker (for local Postgres 17), ~5 minutes.

```bash
git clone <this-repo> && cd detent
uv sync --locked                # toolchain + deps, pinned by uv.lock
uv run detent init              # writes detent.toml, compose.yaml, .env.example
cp .env.example .env            # local placeholder password (never committed)
docker compose up -d --wait     # digest-pinned Postgres 17, loopback only
uv run detent init              # now applies the plain-SQL migrations
uv run detent doctor            # read-only checks incl. the identity self-test
uv run detent demo              # the two-leg flagship story (see below)
uv run detent inspect <effect_id> --dsn '<printed by the demo>'
```

`detent demo` runs the whole thesis in one command, against the deterministic
reference destination (a C2 API: queryable status, **no honored idempotency**):

1. **Detent leg** — an intent keyed on stable business identifiers is persisted
   before dispatch; the destination commits the order but the response is lost
   on cue; the engine process is **really SIGKILLed**; on restart, recovery
   queries the destination *before any redispatch*, settles the record
   `SETTLED_COMMITTED + CONFIRMED_UNIQUE`, and a re-synthesized retry
   (different model wording, same `order_id`) collapses to the same identity
   and is **rejected with evidence**. One destination effect.
2. **B5 contrast leg** — the strongest conventional baseline (durable runtime,
   stable op-IDs, idempotency keys *sent*) under the identical fault schedule
   retries on restart; the C2 destination ignores the key. **Two** destination
   effects, proven by read-back. The demo exits non-zero if this contrast ever
   stops holding — the check is never weakened to keep the demo impressive
   (master doc §8.3/§8.6).

Developer gates: `make check` (docs/schemas/secrets/integrity), `make py-check
py-test` (lint, strict types, import boundaries, unit + property tests),
`make py-test-integration` (real Postgres via `make py-db-up`), or everything:
`make check-all`.

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
