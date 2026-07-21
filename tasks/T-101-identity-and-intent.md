# T-101: Implement the identity module and Intent Registrar

---
id: T-101
status: draft            # opens only when execution-plan P8 is satisfied (P1/DE-1 closed)
depends_on: []
invariant: "master doc §7.2 — keys derive only from stable identifiers, never model output"
---

## Objective

The pure identity module (RFC-001 §1: JCS + SHA-256, `operation_id`, key derivation) and
the Intent Registrar (`registerIntent` semantics), with the M3 identity tests green.

## Why

First code task after ADR-0013's ratification (execution-plan P6 done; P8 gates opening).
Everything downstream keys off identity; RFC-002 §1 pins the registrar semantics.

## Context — read these first

- [docs/rfc-001-first-slice.md](../docs/rfc-001-first-slice.md) §1 (byte-level procedure)
- [docs/rfc-002-engine-design.md](../docs/rfc-002-engine-design.md) §1 (request model),
  §15 item 1 (test design)
- [schemas/intent-contract.schema.json](../schemas/intent-contract.schema.json) (ADR-0019 shape)

## Scope

**Allowed to write:** `pyproject.toml`, `uv.lock`, `src/detent/{identity,contract}/**`,
`tests/**`, Makefile `py-*` targets (ADR-0017 taxonomy), one new ADR proposing the identity
procedure ratification (RFC-001 §1 items 1–4; next free id), this file's status.
**Forbidden:** SQL/ledger code (T-102), adapters, CLI, CI workflows, schema shape changes.

## Acceptance criteria

- [ ] `uv run pytest tests/identity` exits 0, Hypothesis `conformance` profile (≥1,000
      cases/property): permutation invariance; `parameters`/model-output independence;
      sensitivity; cross-process determinism (fresh interpreter, new `PYTHONHASHSEED`).
- [ ] Pinned RFC 8785 vectors reproduce byte-for-byte (external oracle, not the engine).
- [ ] Edge case: `registerIntent` with same identity tuple + different `effect_class`
      returns `identity_conflict` citing the stored record; different `parameters` returns
      the same `effect_id` with a recorded variant digest (RFC-002 §1 table).
- [ ] `make check` and `make py-check py-test` pass.

## Required validation

`make check && make py-check py-test`; attach test-run output.

## Documentation updates

This file's status; the identity ADR (status `proposed`); decisions/README index row.

## Human review triggers — stop and ask if:

- rfc8785 fails any conformance vector (vendor-or-implement is a human decision).
- The RFC-002 §1 registrar semantics prove unimplementable as specified.

## Definition of done

All criteria checked; validation attached; docs updated; no out-of-scope writes; status set.
