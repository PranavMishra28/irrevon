---
title: "CLI reference"
description: "Every irrevon subcommand, captured verbatim from the CLI's own --help output — generated, drift-gated, never paraphrased."
order: 2
generated:
  command: "uv run irrevon --help (+ per-subcommand --help)"
  capturedSha256: "4b8c6ca2488842516ce20657da57c4310cde025b63ef57a6b55a4cef4e1d7121"
claims:
  - quickstart-real
---
Captured verbatim from the CLI's own `--help` output — the engine is the
single source for flags and semantics; this page never paraphrases them.
Regenerate with `pnpm sync:cli` where the engine toolchain (uv) runs.

## `irrevon`

```text
usage: irrevon [-h] [--version] {init,doctor,demo,serve,bench,worker,inspect} ...

Irrevon — reference reconciliation engine for irreversible AI-agent actions. Irrevon
makes no network connections except to the destinations you configure and your own
Postgres; there is no telemetry, no crash reporting, no update checking.

positional arguments:
  {init,doctor,demo,serve,bench,worker,inspect}
    init                scaffold irrevon.toml, compose.yaml, .env.example
    doctor              read-only environment validation
    demo                deterministic lost-response demo with a durable-retry contrast
    serve               loopback read-only workbench server (127.0.0.1 only; GET/HEAD
                        only)
    bench               IrrevonBench harness (fixtures, validation, non-confirmatory
                        smoke)
    worker              continuous single-writer reconciliation service
    inspect             the ledger-only evidence view

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

## `irrevon init`

```text
usage: irrevon init [-h] [--config CONFIG] [--force] [--dir DIR] [--json]

Scaffold local configuration and apply migrations when explicit IRREVON_MIGRATION_DSN
authority is available.

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml (default: search the current directory and
                   parents)
  --force          overwrite scaffold files that already exist
  --dir DIR        directory to scaffold (default: current directory)
  --json           emit one machine-readable result document
```

## `irrevon doctor`

```text
usage: irrevon doctor [-h] [--config CONFIG] [--probe] [--json]

Validate configuration, identity conformance, ledger readiness, adapter declarations,
and credential presence without dispatching.

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml (default: search the current directory and
                   parents)
  --probe          opt into declared read-only liveness calls
  --json           emit one machine-readable check document
```

## `irrevon demo`

```text
usage: irrevon demo [-h] [--config CONFIG] [--seed SEED] [--leg {irrevon,b5,both}]
                    [--keep | --no-keep] [--jsonl] [--artifact ARTIFACT]
                    [--no-artifact]

Run the deterministic lost-response demonstration and compare reconcile-before-retry
with a conventional durable retry.

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to irrevon.toml (default: search the current directory
                        and parents)
  --seed SEED           deterministic demo seed (default: irrevon.toml [demo].seed or
                        42)
  --leg {irrevon,b5,both}
                        run the Irrevon leg, durable-retry contrast leg (`b5`), or
                        both (default: both)
  --keep, --no-keep     retain the demo database for `irrevon inspect`
  --jsonl               emit events followed by the summary as JSON Lines
  --artifact ARTIFACT   write the demo events + summary here on completion (`irrevon
                        serve` exposes it at /api/v1/demo/artifact)
  --no-artifact         skip writing the demo artifact file
```

## `irrevon serve`

```text
usage: irrevon serve [-h] [--config CONFIG] [--port PORT] [--dsn DSN]
                     [--demo-artifact DEMO_ARTIFACT] [--open] [-q] [--json]

Serve the read-only Workbench and evidence API on 127.0.0.1. Only GET and HEAD
requests are accepted.

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to irrevon.toml (default: search the current directory
                        and parents)
  --port PORT           port on 127.0.0.1 (default 5180; 0 binds an ephemeral port —
                        read the real one from the ready line)
  --dsn DSN             override the ledger DSN (e.g. a kept demo database)
  --demo-artifact DEMO_ARTIFACT
                        file backing /api/v1/demo/artifact
  --open                open the workbench in the default browser
  -q, --quiet           suppress HTTP request logs (the ready line is still emitted)
  --json                print the ready line as one JSON document on stdout
```

## `irrevon worker`

```text
usage: irrevon worker [-h] [--config CONFIG] [--dsn DSN] [--interval INTERVAL]
                      [--sweep-interval SWEEP_INTERVAL] [--health-file HEALTH_FILE]
                      [--max-cycles MAX_CYCLES]

Run the single-writer recovery, reconciliation, and orphan-sweep loop.

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to irrevon.toml (default: search the current directory
                        and parents)
  --dsn DSN             override the ledger DSN
  --interval INTERVAL   reconcile-cycle interval in seconds (default 30)
  --sweep-interval SWEEP_INTERVAL
                        orphan-sweep interval in seconds (default 300)
  --health-file HEALTH_FILE
                        freshness file refreshed every cycle (liveness-probe target
                        for non-HTTP deployments)
  --max-cycles MAX_CYCLES
                        stop after N cycles (operational/test affordance; default: run
                        until SIGTERM/SIGINT)
```

## `irrevon inspect`

```text
usage: irrevon inspect [-h] [--config CONFIG] [--reveal] [--json] [--dsn DSN]
                       identifier

Inspect ledger evidence for one effect without contacting a destination.

positional arguments:
  identifier       effect id or stable upstream identifier to inspect

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml (default: search the current directory and
                   parents)
  --reveal         show stable-id values (redacted by default)
  --json           emit one machine-readable evidence view
  --dsn DSN        override the ledger DSN (e.g. a kept demo database)
```

## `irrevon bench`

```text
usage: irrevon bench [-h] [--config CONFIG]
                     {fixtures,validate,smoke,conform,analyze,run,freeze} ...

Develop, validate, and analyze IrrevonBench artifacts. Confirmatory execution remains
refused until the required human freeze verifies.

positional arguments:
  {fixtures,validate,smoke,conform,analyze,run,freeze}
    fixtures            regenerate or verify the committed public dev split
    validate            schema + digest verification of a fixture set
    smoke               non-confirmatory mechanism run against the dev split
    conform             declared-vs-observed capability conformance probes (public
                        adapter surface only)
    analyze             descriptive comparison over completed runs
    run                 confirmatory benchmark run (refused pre-freeze)
    freeze              freeze-registration tooling: draft the machine-verifiable
                        package or verify an existing registration (the freeze act
                        itself is human-only)

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to irrevon.toml (default: search the current directory
                        and parents)
```

## `irrevon bench fixtures`

```text
usage: irrevon bench fixtures [-h] [--dir DIR] [--master-seed MASTER_SEED] (--write |
                              --verify)

Write or deterministically verify a development fixture split.

options:
  -h, --help            show this help message and exit
  --dir DIR             fixture-set directory (default: bench/fixtures/dev)
  --master-seed MASTER_SEED
                        64-hex master seed for a PRIVATE workload set (company
                        adoption path: same structure, schemas, and gates as the
                        public split; never committed here). Default: the public dev
                        seed.
  --write               write the deterministic fixture set
  --verify              verify the fixture set against deterministic regeneration
```

## `irrevon bench validate`

```text
usage: irrevon bench validate [-h] [--dir DIR]

Validate fixture schemas, manifests, and content digests.

options:
  -h, --help  show this help message and exit
  --dir DIR   fixture-set directory (default: bench/fixtures/dev)
```

## `irrevon bench smoke`

```text
usage: irrevon bench smoke [-h] [--fixtures FIXTURES] [--out OUT] [--arms ARMS]
                           [--workloads WORKLOADS] [--dsn DSN] [--enrichment-quirk]
                           [--json]

Run a non-confirmatory mechanism check against development fixtures.

options:
  -h, --help            show this help message and exit
  --fixtures FIXTURES   fixture-set directory (default: bench/fixtures/dev)
  --out OUT             run-output directory (default: .bench-smoke-runs)
  --arms ARMS           comma-separated arm ids (R requires --dsn / a reachable
                        ledger)
  --workloads WORKLOADS
                        comma-separated workload ids (default: all)
  --dsn DSN             Postgres admin DSN (required for arm R)
  --enrichment-quirk    destination stores normalized/enriched payloads (attribution-
                        hardening exercise)
  --json                emit the comparison as JSON
```

## `irrevon bench conform`

```text
usage: irrevon bench conform [-h] [--tier {C1,C2,C3}] [--declaration DECLARATION]
                             [--declared-tier DECLARED_TIER] [--json]

Compare a capability declaration with synthetic reference-destination observations.

options:
  -h, --help            show this help message and exit
  --tier {C1,C2,C3}     reference-destination profile to probe
  --declaration DECLARATION
                        capability declaration JSON (default: the packaged refdest
                        declaration for --tier)
  --declared-tier DECLARED_TIER
                        probe with the declaration of a DIFFERENT tier (drift
                        demonstration)
  --json                emit the conformance report as JSON
```

## `irrevon bench analyze`

```text
usage: irrevon bench analyze [-h] --runs RUNS [--json] [--verdict] [--margin MARGIN]
                             [--worst-cell-gate WORST_CELL_GATE]
                             [--reference-arm REFERENCE_ARM]
                             [--composite-arm COMPOSITE_ARM] [--b5-arm B5_ARM]

Build a descriptive comparison from completed run artifacts.

options:
  -h, --help            show this help message and exit
  --runs RUNS           directory containing completed benchmark runs
  --json                emit the comparison as JSON
  --verdict             additionally run the registered verdict machinery
                        (synthetic/mechanism data only pre-freeze; requires explicit
                        --margin and --worst-cell-gate)
  --margin MARGIN       TOST equivalence margin δ (human parameter; no default)
  --worst-cell-gate WORST_CELL_GATE
                        worst-cell gate in absolute rate points (no default)
  --reference-arm REFERENCE_ARM
                        reference arm id (default: R)
  --composite-arm COMPOSITE_ARM
                        composite comparator arm id (default: B5+B3+B6)
  --b5-arm B5_ARM       durable-runtime comparator arm id (default: B5)
```

## `irrevon bench run`

```text
usage: irrevon bench run [-h] --fixtures FIXTURES [--out OUT] [--arms ARMS]
                         [--dsn DSN]

Attempt a confirmatory run; refuse unless the human-controlled freeze registration
verifies.

options:
  -h, --help           show this help message and exit
  --fixtures FIXTURES  frozen fixture-set directory
  --out OUT            run-output directory (default: bench/runs)
  --arms ARMS          comma-separated arm ids (default: registered arms)
  --dsn DSN            Postgres admin DSN when a selected arm requires it
```

## `irrevon bench freeze`

```text
usage: irrevon bench freeze [-h] --stage {A,B} (--draft-out DRAFT_OUT | --verify)

Draft freeze bindings or verify an existing human-created registration. This command
never performs the freeze act.

options:
  -h, --help            show this help message and exit
  --stage {A,B}         registration stage to draft or verify
  --draft-out DRAFT_OUT
                        write registration.draft.json (bindings filled, human fields
                        sentinelled — can never verify)
  --verify              verify docs/registrations/stage-<s>-v1/registration.json
```
