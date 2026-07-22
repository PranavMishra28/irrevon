# Irrevon

**IrrevonBench, a fault-injection benchmark for irreversible AI-agent actions, and Irrevon,
its reference reconciliation engine.** The benchmark plan is written for preregistration
and is currently a draft; no section is frozen
([docs/benchmark-preregistration.md](docs/benchmark-preregistration.md) §0).

When an LLM agent crosses into an irreversible external action and the outcome is ambiguous —
a lost response, a crash mid-call, or a retry with re-synthesized arguments — duplicate,
orphaned, or lost effects follow. IrrevonBench is designed to measure how often that happens
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
Also in: the CI pipeline (required PR gate + nightly; [docs/ci.md](docs/ci.md)); the
read-only workbench frontend ([web/](web/README.md)) with a loopback live mode over
`irrevon serve` ([ADR-0024](docs/decisions/0024-serve-read-surface.md)); wheel/sdist
packaging with `make dist` / `dist-smoke` (built, unpublished); the expanded
marketing/discovery site ([site/](site/README.md) — built, deploy gated); and the
**IrrevonBench foundation layer** ([docs/benchmark.md](docs/benchmark.md), ADR-0030
proposed): benchmark contracts, deterministic public dev fixtures, the baseline-ladder
arm registry, fault orchestration, a two-oracle scoring pipeline (destination read-back
+ causal-history checker, cross-checked per run), metrics + a stdlib statistics
pipeline, and `irrevon bench` — with confirmatory runs mechanically refused until the
human freeze registrations pass verification (ADR-0033). Also in: the continuous
single-writer service (`irrevon worker` — [docs/operations.md](docs/operations.md)) and
credential-gated DRAFT provider adapters (Stripe C1 / EasyPost C2 — never live-called;
ADR-0010/0012 remain the human spikes).
Live sandbox runs, confirmatory benchmark evidence (M7, human-gated), and any packaged
release remain gated by the execution plan. The roadmap, gates, and what blocks what are
in [docs/execution-plan.md](docs/execution-plan.md). Items awaiting human decision are
in [docs/review-queue.md](docs/review-queue.md).

## Quickstart — run the flagship demo

Prerequisites: [uv](https://docs.astral.sh/uv/), Docker (for local Postgres 17), ~5 minutes.

```bash
git clone <this-repo> && cd irrevon
uv sync --locked                # toolchain + deps, pinned by uv.lock
uv run irrevon init              # writes irrevon.toml, compose.yaml, .env.example
cp .env.example .env            # local placeholder password (never committed)
docker compose up -d --wait     # digest-pinned Postgres 17, loopback only
uv run irrevon init              # now applies the plain-SQL migrations
uv run irrevon doctor            # read-only checks incl. the identity self-test
uv run irrevon demo              # the two-leg flagship story (see below)
uv run irrevon inspect <effect_id> --dsn '<printed by the demo>'
```

`irrevon demo` runs the whole thesis in one command, against the deterministic
reference destination (a C2 API: queryable status, **no honored idempotency**):

1. **Irrevon leg** — an intent keyed on stable business identifiers is persisted
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

Developer gates: `make check` (docs/schemas/secrets/integrity/workflows), `make py-check
py-test` (lint, strict types, import boundaries, unit + property tests),
`make py-test-integration` (real Postgres via `make py-db-up`), `make web-check
web-test` (workbench static gates + unit/story tests), or everything:
`make check-all`.

## Workbench (`web/`)

A local-first, **read-only** evidence workbench over the engine's contracts. Two
data modes, never mixed: fixture-backed (captured transcripts of the real engine;
dev/test/review only) and **live mode** against the loopback read server
(`irrevon serve` — GET/HEAD-only, `irrevon_read` SELECT-only role, 127.0.0.1
only; [ADR-0024](docs/decisions/0024-serve-read-surface.md)). The browser can
never mutate anything in either mode. The v0.2 redesign adds an honest Overview at
`/` (complete-snapshot counts with explicit refusals), a custom-SVG causal
investigation graph on effect detail (single-effect only — see the A1 note in
[docs/review-queue.md](docs/review-queue.md) §2), the six-layer surface system,
and a responsive shell down to 375 px (mobile drawer navigation). Toolchain
(Node 24 + pnpm 11), dev commands (`pnpm dev`, `pnpm check`, `pnpm e2e`,
`pnpm vrt`), dependency register, and budgets are documented in
[web/README.md](web/README.md).

## Marketing site (`site/`)

A zero-JS-by-default Astro package: the six original pages plus the discovery
surface (drift-gated rendered repository docs with self-hosted search, the
recorded interactive demo, research/changelog/roadmap/install, full SEO
metadata), a drift-gated claims registry, and identity vendored from the
workbench tokens. Deployed to Vercel at the origin root by owner directive
([ADR-0027](docs/decisions/0027-site-vercel-deploy.md)); deploys remain
human-gated acts (the reconciliation record lives in
[docs/review-queue.md](docs/review-queue.md)). See [site/README.md](site/README.md).

## Repository status and licensing

This repository is public and licensed under **Apache-2.0** ([LICENSE](LICENSE) +
[NOTICE](NOTICE); decision record [ADR-0028](docs/decisions/0028-apache-2-license.md),
owner-ratified 2026-07-21) — but it is **not yet released software**: nothing is on any
package index, and **no contributions are accepted** while the contributor-governance
half of [ADR-0014](docs/decisions/0014-licensing.md) (DCO, inbound policy) remains open.
Packaged releases, published artifacts, and the contribution policy arrive only through
the public-release gate in [docs/execution-plan.md](docs/execution-plan.md). See
[LICENSING.md](LICENSING.md).

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
make tools   # one-time: checksum-pinned actionlint/zizmor bootstrap, then install
             # lychee, check-jsonschema, gitleaks, pre-commit (Homebrew) and verify
             # installed versions against the tested pins
make check   # links + schemas + secrets + integrity + workflow lint + frozen-file gate
```

`make check` is the required local gate (pre-commit additionally runs the secret scan on
every commit). It verifies internal links (offline, deterministic), validates JSON Schemas
and their valid/invalid example suites, scans for secrets, checks repository integrity
(master-doc hash pin, ADR id uniqueness), lints the GitHub workflows (actionlint + offline
zizmor), and enforces the frozen/append-only file rules. CI runs exactly these make targets
(local parity — [docs/ci.md](docs/ci.md)); the full local ladder is `make check-all`.
