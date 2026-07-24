---
title: "Getting started"
description: "From clone to the recorded flagship demo: uv, Docker, irrevon init, doctor, and the two-leg demo run."
order: 1
badge: "recorded"
claims:
  - quickstart-real
  - not-published
  - demo-sequence
  - demo-contrast
---

Irrevon is pre-release: nothing is on a package index; the repository is licensed
Apache-2.0. The only install path today is a clone, with a deterministic demo at the
end of it. Planned distribution is documented on the [install page](/install/), future
tense.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — resolves the pinned toolchain and dependencies from `uv.lock`.
- Docker — runs a local, digest-pinned Postgres 17 on loopback. Nothing else.
- Git.

Irrevon makes no network connections except to the destinations you configure and your
own Postgres: no telemetry, no crash reporting, no update checking.

## Clone and set up

```bash
git clone https://github.com/PranavMishra28/irrevon.git
cd irrevon

uv sync --locked                # toolchain + deps, pinned by uv.lock
uv run irrevon init             # writes irrevon.toml, compose.yaml, .env.example
cp .env.example .env            # local migration bootstrap; no credential
set -a && . ./.env && set +a    # make the migration-only DSN available
docker compose up -d --wait     # digest-pinned Postgres 17, loopback only
uv run irrevon init             # now applies the plain-SQL migrations
```

`init` is idempotent and two-phase by design: the first run scaffolds configuration, the
second (with the database up) applies the migrations under the append-only journal
discipline.

## Verify the environment

```bash
uv run irrevon doctor           # non-destructive checks; includes a rolled-back write probe
```

`doctor` is non-destructive, but it is not strictly read-only: it validates the database
roles and migration journal, performs a rolled-back temporary-table write probe, and runs
the identity self-test (the same derivation the conformance suite property-tests). If a
check fails, the message tells you exactly which layer to fix. For a stale pre-rename
database, the following reset deletes the disposable local PostgreSQL volume before
restarting PostgreSQL and initializing it again:

```bash
docker compose down -v
docker compose up -d --wait
uv run irrevon init
```

Do not use this destructive reset against a volume containing data you need to keep.

## Run the flagship demo

```bash
uv run irrevon demo             # the two-leg flagship story
```

The demo runs the same fault schedule twice — a lost dispatch response, a real SIGKILL,
and a re-synthesized retry — once through the Irrevon engine and once through a
developmental file-journal durable-runtime comparison (benchmark arm B5: durable retry,
stable operation IDs, idempotency keys sent), both against the queryable reference
destination (tier C2). A real Temporal comparator remains a prerequisite for the
operational freeze (Stage B).

## What you should see

The sequence below is the recorded artifact from a real run (seed 777) — the same
artifact the [interactive demo page](/demo/) renders. Your run replays the same
deterministic schedule:

```text
Irrevon leg
  registered                  lifecycle PERSISTED
  dispatch_response_lost      fault response_lost · lifecycle AMBIGUOUS
  crash                       exit_status -9 (a real SIGKILL)
  recovered                   scanned 1 · adjudicated 1 — before any redispatch
  settled_confirmed_unique    SETTLED_COMMITTED · CONFIRMED_UNIQUE
  resynthesis_collapsed       replayed true (same identity, different wording)
  duplicate_rejected          denied · deny_check dedup · decision_id 2

Durable-runtime contrast leg (benchmark arm B5; identical fault schedule)
  b5_response_lost            transport_outcome LOST
  b5_restart                  durable runtime restarts the workflow
  b5_retried                  key sent — the queryable tier-C2 destination ignores it
  b5_duplicate                destination_effects 2
```

One leg ends with one destination effect and a refused duplicate; the other ends with
two. That contrast — recorded, reproducible, never dramatized — is the project's whole
argument, and the demo asserts it (`contrast_holds`) rather than assuming it.

## Where to go next

- [Integration guide](/docs/integration/) — wiring `register_intent` → `dispatch` into an agent's tool boundary.
- [Architecture](/docs/architecture/) — what each component does and why the ledger is append-only.
- [CLI reference](/docs/cli-reference/) — every subcommand, captured from the CLI's own `--help`.

## Uninstall

Nothing global is installed. Remove the clone, run `docker compose down -v` to drop the
local database volume, and delete the project-local files (`irrevon.toml`, `.env`,
`compose.yaml`).
