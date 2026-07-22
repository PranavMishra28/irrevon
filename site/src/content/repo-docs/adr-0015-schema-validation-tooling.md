---
title: "JSON Schema 2020-12 + check-jsonschema/lychee/gitleaks orchestrated by Make"
sourcePath: "docs/decisions/0015-schema-validation-tooling.md"
sourceSha256: "7d32e0d7ecabe73259d1f72f03ab159fab00fc20fb0d3cf1fa78604bccfdf6ec"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0015"
  status: "accepted"
  date: "2026-07-20"
  supersedes: "—"
---

## Context

The scaffold needs machine-validated contracts and a deterministic local gate **without
choosing an implementation language** (ADR-0013 is open). Criteria: brew-installable, offline
and deterministic, clear exit codes for agents, no heavy toolchain. A dev tool's
implementation language does not constitute a language decision for Detent.

## Decision

- **Schema dialect: JSON Schema draft 2020-12** — current, broadly supported dialect. One
  schema resource per file; absolute placeholder `$id`s pending the name screen (see
  [../../schemas/README.md](../../schemas/README.md)); shape/enums/required-fields only —
  cross-record invariants and transition legality live in RFC prose and conformance tests,
  not `if/then` contortions.
- **Schema validation: check-jsonschema** — `--check-metaschema` validates the schema files
  themselves (the likeliest agent-authoring failure mode); validates JSON and YAML instances;
  active project. Wired so valid examples must pass and invalid examples must fail.
- **Link integrity: lychee `--offline --include-fragments`** — checks relative paths and
  heading anchors with zero network, so the gate is deterministic; external URLs are
  deliberately unchecked in the gate.
- **Secret scan: gitleaks** (`dir` + `git` once a repo exists) — fast, offline, default rules
  extended by a generic-only `.gitleaks.toml`; also runs as the pre-commit hook.
- **Orchestration: Make** (`make check`) — preinstalled everywhere the repo will run; every
  agent knows it; survives the docs→code transition.
- Plus a small repo-integrity script (`scripts/check-integrity.sh`): master-doc hash pin, ADR
  id uniqueness, `.cursor` JSON syntax, optional untracked-tripword scan.

Tested versions: lychee 0.24.2 · check-jsonschema 0.37.4 · gitleaks 8.30.1 · pre-commit 4.6.0.

## Alternatives

- **ajv-cli** — fastest engine but the CLI is sparsely maintained (last release 2021) and
  wants an npm project; fine as a future cross-check, not the backbone.
- **sourcemeta `jsonschema` CLI** — strong purpose-built alternative (schema `test`
  subcommand, lint/fmt); not adopted now to keep the tool count minimal; reopen if dialect-
  interpretation disagreements ever matter.
- **yajsv** — no 2020-12 support; unmaintained. Ruled out.
- **markdownlint** — cut as validation theater: style-linting prose protects no invariant and
  generates noise commits.
- **adr-tools / log4brains** — dormant or aimed at multi-team publishing; a template + index
  table is the whole process at this scale.
- **just** — nicer syntax than Make but an extra install everywhere else; zero needed features
  Make lacks.

## Consequences

`make check` = links + schemas + secrets + integrity, all offline/deterministic. Schema
changes remain ADR-gated (see `.cursor/rules/contracts.mdc`). Deferred record schemas are
listed with reasons in `schemas/README.md`.

## Risks

Unpinned brew installs can drift tool versions between machines; tested versions are recorded
here and in the Makefile header and updated deliberately.

## Reopen trigger

A 2020-12 successor dialect gains broad tooling support; check-jsonschema goes unmaintained;
or schema validation disagreement between implementations is observed.
