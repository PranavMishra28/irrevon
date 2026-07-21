# T-000: Recommend the implementation language and core stack (ADR-0013 proposal)

---
id: T-000
status: done
depends_on: []
invariant: "none — this is a decision task, not code; no product code may be written"
---

> **Completed 2026-07-21:** the proposal appended to ADR-0013 was ratified in writing by
> the owner; ADR-0013 is accepted (Python 3.13 / uv / pytest+Hypothesis / psycopg 3 /
> rfc8785). This file is retained as the append-only task record.

## Objective

A completed language/stack comparison and proposed decision text for
[ADR-0013](../docs/decisions/0013-implementation-language.md), ready for human ratification.
**This task produces a recommendation, not a decision, and writes no code.**

## Why

No implementation task can open before ADR-0013 closes (execution-plan P6→P8). The evidence
and leaning are recorded in the ADR's Context section; what remains is a current
primary-source check and a structured comparison.

## Context — read these first

- [docs/decisions/0013-implementation-language.md](../docs/decisions/0013-implementation-language.md) — criteria + evidence + leaning
- [docs/master-doc.md](../docs/master-doc.md) §3.1 (builder constraints), §12.2 (≥1,000
  property cases/invariant), §14.1 (career success definition)
- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §1 (JCS/SHA-256 encoder needed)

## Scope

**Allowed to write:** a proposal section appended to ADR-0013 (below its Decision section,
clearly marked `PROPOSED — awaiting ratification`); this file's status.
**Forbidden:** flipping ADR-0013's status (human-only); any code, package manifest, or
toolchain file; any other file.

## Acceptance criteria

- [x] Candidate set evaluated: at least Python, TypeScript/Node, Go, Rust.
- [x] Each candidate scored, with citations to current primary sources, on: property-testing
      framework maturity (must sustain ≥1,000 cases/invariant), Postgres driver quality,
      RFC 8785 (JCS) encoder availability, coding-agent fluency, solo maintainability, and
      adoption credibility with the project's primary audience — engineers and researchers
      in the agent-framework ecosystem (master doc §3.1, §14.1).
- [x] A single recommendation with the one-line reason each alternative lost (ADR
      Alternatives format), plus proposed Decision text for ADR-0013.
- [x] Negative findings recorded (anything that surprised against the Python leaning).
- [x] `make check` passes.

## Required validation

`make check`; attach the comparison table and proposed ADR text in the task output.

## Documentation updates

This file's status → `blocked-human-review`. Nothing else (the ADR flip is the human's).

## Human review triggers — stop and ask if:

- The evidence contradicts the recorded leaning strongly enough that the ADR's Context
  section itself seems wrong.
- Any criterion cannot be evaluated without running code or installing toolchains (out of
  scope for a docs-only repo).

## Definition of done

All criteria checked; proposal appended to ADR-0013 marked PROPOSED; status set to
`blocked-human-review`; ratification awaited.
