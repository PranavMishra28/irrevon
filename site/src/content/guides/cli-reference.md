---
title: "CLI reference"
description: "Every irrevon subcommand, captured verbatim from the CLI's own --help output — generated, drift-gated, never paraphrased."
order: 2
generated:
  command: "uv run irrevon --help (+ per-subcommand --help)"
  capturedSha256: "66fc48769f2a396269fe9425ab34976593201557daa531d9fce93365ecd1bebd"
claims:
  - quickstart-real
---
Captured verbatim from the CLI's own `--help` output — the engine is the
single source for flags and semantics; this page never paraphrases them.
Regenerate with `pnpm sync:cli` where the engine toolchain (uv) runs.

## `irrevon`

```text
usage: irrevon [-h] [--version] {init,doctor,demo,inspect} ...

Irrevon — reference reconciliation engine for irreversible AI-agent actions. Irrevon
makes no network connections except to the destinations you configure and your own
Postgres; there is no telemetry, no crash reporting, no update checking.

positional arguments:
  {init,doctor,demo,inspect}
    init                scaffold irrevon.toml, compose.yaml, .env.example
    doctor              read-only environment validation
    demo                the flagship demo incl. the B5 contrast leg
    inspect             the ledger-only evidence view

options:
  -h, --help            show this help message and exit
  --version             show program's version number and exit
```

## `irrevon init`

```text
usage: irrevon init [-h] [--config CONFIG] [-q] [--no-color] [--force] [--dir DIR]
                    [--json]

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml
  -q, --quiet
  --no-color
  --force
  --dir DIR
  --json
```

## `irrevon doctor`

```text
usage: irrevon doctor [-h] [--config CONFIG] [-q] [--no-color] [--probe] [--json]

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml
  -q, --quiet
  --no-color
  --probe          opt into declared read-only liveness calls
  --json
```

## `irrevon demo`

```text
usage: irrevon demo [-h] [--config CONFIG] [-q] [--no-color] [--seed SEED]
                    [--leg {irrevon,b5,both}] [--keep | --no-keep] [--jsonl]

options:
  -h, --help            show this help message and exit
  --config CONFIG       path to irrevon.toml
  -q, --quiet
  --no-color
  --seed SEED
  --leg {irrevon,b5,both}
  --keep, --no-keep     retain the demo database for `irrevon inspect`
  --jsonl
```

## `irrevon inspect`

```text
usage: irrevon inspect [-h] [--config CONFIG] [-q] [--no-color] [--reveal] [--json]
                       [--dsn DSN]
                       identifier

positional arguments:
  identifier

options:
  -h, --help       show this help message and exit
  --config CONFIG  path to irrevon.toml
  -q, --quiet
  --no-color
  --reveal         show stable-id values (redacted by default)
  --json
  --dsn DSN        override the ledger DSN (e.g. a kept demo database)
```
