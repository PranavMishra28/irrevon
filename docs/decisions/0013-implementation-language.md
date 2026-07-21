---
id: ADR-0013
title: Choose the implementation language and core stack
status: open
date: 2026-07-20
supersedes: —
---

## Context

Deliberately deferred so the absence of a decision is not mistaken for an accident. No code
may be written before this closes. Evidence gathered pre-scaffold:

- **Ecosystem gravity is Python-first** `[EI]`: the integration surface (LangGraph, CrewAI),
  the OSS twins (agent-ledger, SafeAgent), the closest academic system (Atomix), and the
  nearest funded entrant's SDK (Bylaw) are all Python. Python maximizes integration
  credibility and contributor pool for the audience that matters (§14.1 career signal).
- **Property testing is a hard requirement** (§12.2: ≥1,000 cases/invariant): candidate
  ecosystems must have a mature framework (Hypothesis / proptest / fast-check / jqwik-class).
- **Storage:** Postgres is an inherited constraint (ADR-002/§6.1 — single-writer append-only
  ledger, row locking), not reopened here; every candidate has a mature driver, so it cannot
  disqualify any option. A **SQLite-quickstart / Postgres-benchmark** split is an option worth
  weighing for the <30-minute stranger test (Atomix ships SQLite; precedent exists) `[EI]`.
- **Coding-agent fluency** (training-data density) and solo maintainability at ~10 hrs/week
  weigh heavily for a solo builder.
- The deterministic core is pure logic + I/O at the edges; no performance argument for a
  systems language has been made.

## Decision

**OPEN — NOT decided.** Current leaning `[EI]`: **Python** for the POC, with the ledger
schema kept language-neutral (SQL migrations) so a second SDK remains possible.

Process: [tasks/T-000](../../tasks/T-000-language-stack-spike.md) (a recommendation spike, not
code) produces the comparison and proposed decision text for this ADR; **the human ratifies**
by filling in the Decision section and flipping status to accepted. The first code task is
blocked on that ratification (execution-plan P6→P8).

## Alternatives

To be evaluated by T-000 against the criteria above; candidates at minimum: Python,
TypeScript/Node, Go, Rust. Each rejection gets its one-line reason here at ratification.

## Consequences

Closes the toolchain for M2 bootstrap (test runner, property-test framework, Postgres driver,
migration tooling); unlocks the RFC-001 identity ADR (JCS encoder availability check per
candidate).

## Risks

Choosing for ecosystem gravity over type-safety may cost refactoring ease later; the
language-neutral RFC/schemas bound that risk (a rewrite re-implements against frozen
contracts).

## Reopen trigger

Start of M3 implementation without ratification (blocks); or the frontier-lab audience signal
shifts materially away from the chosen ecosystem.
