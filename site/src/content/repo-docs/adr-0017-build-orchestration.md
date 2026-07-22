---
title: "Build orchestration — plain Make over uv/pnpm native layers, with measured adoption triggers for graph-based build systems"
sourcePath: "docs/decisions/0017-build-orchestration.md"
sourceSha256: "aea59440a95c9528a2c980e86e41e48c1d06716fa20022fd8370cf89361cbfba"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0017"
  status: "accepted (ratified in writing by the owner, 2026-07-21)"
  date: "2026-07-21"
  supersedes: "—"
---

## Context

The repo is becoming a two-package monorepo: a Python engine+bench (ADR-0013:
uv/pytest/Hypothesis) and a TypeScript web workbench (ADR-0016), joined only by the
language-neutral `schemas/` contract. `make check` is the established universal gate
(AGENTS.md; Makefile) and currently runs in ~1.7–2.2 s (measured 2026-07-21). The staged CI
design (arriving via the CI workstream; see docs/ci.md once landed) already runs make
targets in path-filtered workflows. The full dependency graph is three nodes and two edges
(docs; schemas→py; schemas→web). Project policy (derived from master doc §8/§12.2) forbids
letting test/benchmark correctness depend on cache state — which neutralizes the core value
proposition (task-result replay) of graph-based build tools for the most expensive suites.
Tool states verified against primary sources 2026-07: Turborepo remains JS-conventioned
(Python only via package.json shims); Nx needs a third-party single-maintainer Python
plugin and suffered the Aug 2025 s1ngularity npm compromise; Pants is maintained (2.32.1,
2026-06) but heavy for a 3-node graph; Bazel's uv support is lockfile-generation-only;
Buck2 has no stable release; Dagger has repositioned as a containerized-workflow/agent
engine; Just adds no caching or affected execution over Make.

## Decision

Keep plain GNU Make as the single command surface and CI parity contract. Delegate
dependency and workspace management to the native layers — uv (Python) and pnpm (web).
Implement affected-target execution with per-workflow GitHub Actions path filters, with
`schemas/**` and `Makefile` in every code workflow's paths. Adopt the target taxonomy:
`check` (links+schemas+secrets+integrity, ≤2 min, unchanged scope), `py-check`, `py-test`,
`py-test-integration`, `web-check`, `web-test`, `check-all`. Every CI job runs exactly one
make target; no bespoke inline scripts in workflows.

**Deferred from the original draft** (per the 2026-07-21 simplification review, accepted):
the diff-based `scripts/check-frozen.sh` frozen/append-only gate is not adopted now — the
state-based master-doc hash pin already catches byte drift, and the diff layer only becomes
enforcing once branch protection/rulesets are configured (free on the public repo;
human-only settings change). Adopt it in the same change that configures required checks.

## Alternatives

- Just — command runner with no caching/affected execution: fixes nothing Make lacks,
  costs Make's incumbency and agent fluency.
- Turborepo — cannot see the Python half without package.json shims.
- Nx + @nxlv/python — best polyglot graph, but adds an npm root dependency (fresh
  s1ngularity compromise) and a single-maintainer plugin for a two-edge graph.
- Pants — maintained and Python-native, but daemon + upgrade train + BUILD discipline are
  disproportionate at this scale; TS support experimental.
- Bazel / Buck2 — hermeticity and exact graphs at a configuration cost that dwarfs the
  repo; Buck2 additionally has no stable release and BYO Python toolchains.
- Dagger — containerized-pipeline/agent engine; wrong layer for local task running.

## Consequences

Easier: onboarding (one command), agent operation (Make known cold), CI/local parity (same
targets), supply chain (zero new orchestrator dependencies). Harder: no task-result caching
(accepted — partially forbidden by policy anyway); path filters are hand-maintained
(mitigated by the schemas/Makefile rule; drift is a reopen trigger). Conformance: CI
workflow bodies must be `make <target>` one-liners; `make check` wall time budgeted ≤2 min.

## Risks

Path-filter drift silently skipping an affected suite (bounded by local `check-all` and
nightly full runs; trigger T3). Hypothesis suite growth making dumb re-execution painful
before triggers fire (first levers: pytest selection, CI sharding — not build-graph
caching).

## Reopen trigger

Any of (measured): T1 warm `make check` > 60 s or `make check-all` > 10 min; T2
demonstrably duplicated CI work > 200 min/month; T3 two path-filter drift incidents in a
quarter; T4 > 3 packages in one ecosystem or a build-order-bearing codegen edge; T5 need
for remote execution / shared cache (second regular contributor); T6 externally demanded
bit-reproducible builds. T1+T2 together, or T3 twice, defaults the re-run toward adopting a
graph-based tool.
