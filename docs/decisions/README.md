# Architecture Decision Records — index and policy

## Why most settled decisions have no file here

ADRs 001–009 and 011 are **canonical in master doc §11** ([../master-doc.md](../master-doc.md)),
which carries each decision's rejected alternative and reopen trigger, frozen inside the
hash-pinned document. Duplicating them as files would create a second source of truth that can
drift (split-brain). Files exist only for decisions that are **OPEN** (still being made) or
**NEW** (not in §11). When a §11 decision is superseded or reopened, a full ADR file is
created *then*, per §12.5/§17 — which is when append-only file history becomes necessary.

## Index (complete: 0000–0034)

| ADR | Title | Status | Canonical text |
|---|---|---|---|
| 0000 | Scope freeze | accepted (countersign pending); wording of one non-goals bullet superseded by ADR-0026 (decision content unchanged) | [0000-scope-freeze.md](0000-scope-freeze.md) |
| 0001 | Identity from stable upstream identifiers | accepted | master doc §11 |
| 0002 | Persist-before-dispatch; append-only ledger | accepted | master doc §11 |
| 0003 | Destination capability tiers C1/C2/C3 | accepted | master doc §11 |
| 0004 | Three orthogonal state dimensions | accepted | master doc §11 |
| 0005 | Adapter contract incl. cited capability declaration | accepted | master doc §11 |
| 0006 | Deterministic authority; model advisory-only | accepted | master doc §11 |
| 0007 | Compensation is a new intent, never rollback | accepted | master doc §11 |
| 0008 | Frozen seeded oracle; client-side fault injection | accepted | master doc §11 |
| 0009 | Benchmark-first, C2-scoped | accepted | master doc §11 |
| 0010 | Stripe API version pin | **OPEN** | [0010-stripe-api-version.md](0010-stripe-api-version.md) |
| 0011 | Working name "Detent" | **superseded by ADR-0023** (screen fired its reopen trigger) | master doc §11 |
| 0012 | C2 sandbox selection | **OPEN** | [0012-c2-sandbox.md](0012-c2-sandbox.md) |
| 0013 | Implementation language and stack | accepted (ratified 2026-07-21) | [0013-implementation-language.md](0013-implementation-language.md) |
| 0014 | Licensing and contributor governance | license half resolved by ADR-0028 (Apache-2.0, owner ratification 2026-07-21); contributor-governance half **OPEN** | [0014-licensing.md](0014-licensing.md) |
| 0015 | Schema dialect and validation tooling | accepted (countersign requested, review-queue §3) | [0015-schema-validation-tooling.md](0015-schema-validation-tooling.md) |
| 0016 | Frontend workbench stack (Vite SPA + TanStack) | accepted (ratified 2026-07-21) | [0016-frontend-workbench-stack.md](0016-frontend-workbench-stack.md) |
| 0017 | Build orchestration (plain Make over uv/pnpm) | accepted (ratified 2026-07-21) | [0017-build-orchestration.md](0017-build-orchestration.md) |
| 0018 | Distribution model (single PyPI package, $0 infra) | accepted (ratified 2026-07-21) | [0018-distribution-model.md](0018-distribution-model.md) |
| 0019 | Record schemas and API contracts | accepted (ratified 2026-07-21) | [0019-record-schemas-and-api-contracts.md](0019-record-schemas-and-api-contracts.md) |
| 0020 | Identity procedure (JCS + SHA-256, RFC-001 §1 items 1–4) | **proposed** | [0020-identity-procedure.md](0020-identity-procedure.md) |
| 0021 | Record schemas admitted at M3 (ADR-0019 criteria) | **proposed** | [0021-record-schemas-admission.md](0021-record-schemas-admission.md) |
| 0022 | Migration runner (in-package plain-SQL, hash journal) | **proposed** | [0022-migration-runner.md](0022-migration-runner.md) |
| 0023 | Rename: Detent → Irrevon; DetentBench → IrrevonBench | accepted (owner written directive 2026-07-21; supersedes ADR-011) | [0023-rename-to-irrevon.md](0023-rename-to-irrevon.md) |
| 0024 | `irrevon serve` — loopback read-only workbench surface | accepted (owner serve directive 2026-07-21) | [0024-serve-read-surface.md](0024-serve-read-surface.md) |
| 0025 | Marketing site + discovery surface (`site/`), deploy gated | accepted (owner rebuild directive 2026-07-21); deploy mechanics (items 4–5) superseded by ADR-0027 | [0025-site-discovery-surface.md](0025-site-discovery-surface.md) |
| 0026 | Sanitization supersession of ADR-0000's non-goals wording | **proposed** (owner countersign required) | [0026-scope-freeze-wording-sanitization.md](0026-scope-freeze-wording-sanitization.md) |
| 0027 | Site hosting — Vercel at the origin root (retires the Pages plan) | accepted (owner deploy directive 2026-07-21; supersedes ADR-0025 items 4–5) | [0027-site-vercel-deploy.md](0027-site-vercel-deploy.md) |
| 0028 | Outbound license — Apache-2.0 for the whole repository | accepted (owner ratification 2026-07-21; resolves ADR-0014's license half) | [0028-apache-2-license.md](0028-apache-2-license.md) |
| 0029 | Site telemetry — first-party Vercel Web Analytics + Speed Insights | accepted (owner platform directive 2026-07-21; amends ADR-0025's site posture) | [0029-site-vercel-analytics.md](0029-site-vercel-analytics.md) |
| 0030 | IrrevonBench foundation — bench contracts, harness architecture, integrity gates | **proposed** (owner bench directive 2026-07-22) | [0030-bench-harness-contracts.md](0030-bench-harness-contracts.md) |
| 0031 | Benchmark ecosystem posture — native core; Inspect optional later; NeMo patterns-only; no Toxiproxy; HF prepared-not-published | **proposed** (owner bench directive 2026-07-22) | [0031-bench-ecosystem-interop.md](0031-bench-ecosystem-interop.md) |
| 0032 | Causal effect histories + checker, capability conformance verification, oracle attribution hardening | **proposed** (owner follow-on directive 2026-07-22) | [0032-causal-histories-and-conformance.md](0032-causal-histories-and-conformance.md) |
| 0033 | Machine-verifiable freeze registrations; adapter attribution declarations; site build provenance | **proposed** (owner completion directive 2026-07-22) | [0033-verifiable-freeze-and-attribution-declarations.md](0033-verifiable-freeze-and-attribution-declarations.md) |
| 0034 | Continuous worker service; provider-adapter framework (Stripe/EasyPost drafts); multi-worker + Temporal-baseline designs | **proposed** (owner completion directive 2026-07-22) | [0034-continuous-worker-and-provider-adapters.md](0034-continuous-worker-and-provider-adapters.md) |

## Policy

- **Statuses:** `proposed → open → accepted → deprecated | superseded by ADR-NNNN`.
- **Append-only:** never rewrite an accepted ADR's decision content. Supersede with a new ADR;
  the only edits to the old file are its status line and this index. Typo/link fixes are
  allowed; anything touching context/decision/consequences is a new ADR.
- **The sanctioned open→accepted flip:** filling in an OPEN ADR's decision section and
  flipping status is the one in-place edit — and it is **human-only**. Agents propose; humans
  ratify.
- **Numbering:** `NNNN-short-title.md`, next free id, ids never reused (`make integrity`
  enforces uniqueness). Gaps are fine.
- Invariant-affecting changes (state model, guarantees, identity rules, ledger properties,
  benchmark plan, security controls) require an ADR **before** merge (§12.5).
- Every ADR carries a concrete reopen trigger — the quarterly review (§14.2, O-3) audits them.

## Template

```markdown
---
id: ADR-NNNN
title: <problem–solution phrasing>
status: open | proposed | accepted | superseded by ADR-NNNN
date: YYYY-MM-DD
supersedes: —
---

## Context
<!-- Problem, forces, constraints. Cite master doc §s and external evidence. -->

## Decision
<!-- One paragraph, active voice. For OPEN ADRs: the question + current leaning, labeled. -->

## Alternatives
<!-- Each rejected option with the one-line reason it lost. -->

## Consequences
<!-- What becomes easier/harder; the conformance test(s) that enforce it (§12.1). -->

## Risks
<!-- What could make this wrong, and the blast radius. -->

## Reopen trigger
<!-- Concrete, observable condition forcing a revisit. -->
```
