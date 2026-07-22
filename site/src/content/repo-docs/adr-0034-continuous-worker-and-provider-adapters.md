---
title: "Continuous worker service, provider-adapter framework (Stripe C1 / EasyPost C2 drafts), and the multi-worker + independent-baseline designs"
sourcePath: "docs/decisions/0034-continuous-worker-and-provider-adapters.md"
sourceSha256: "2b5949c715f52c1a5ad9a671aee2cbeccd55ccb89738bb7d6283e46f27d0304e"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0034"
  status: "proposed"
  date: "2026-07-22"
  supersedes: "—"
---

## Context

The completion directive requires a production-capable self-hosted runtime
(continuous dispatch/reconciliation/sweeps, graceful shutdown, health checks,
a multi-worker strategy) and credential-gated real-provider adapters —
without weakening the ratified single-writer invariant (ADR-002) or
pre-empting the human ADR-0010/0012 decisions. Research findings this rests
on (primary sources, 2026-07-22, recorded in the PR): Postgres job systems
converge on `FOR UPDATE SKIP LOCKED` claiming with short transactions,
lease/heartbeat columns plus a rescuer (River/Oban/pg-boss), and none
implement Kleppmann-style fencing — their rescuers tolerate duplicate
execution, which Irrevon, of all systems, must not; Kubernetes probe and
SIGTERM-grace conventions; Temporal's dev server is a single MIT binary
whose documented activity guidance (at-least-once + idempotency key) IS the
B5 construct; Restate's server is BSL 1.1; DBOS is a Postgres-backed
library architecturally too close to Irrevon to serve as an independent
baseline. Stripe/EasyPost semantics per the provider fact sheets (review
queue).

## Decision

1. **`irrevon worker` ships now as the continuous single-writer service.**
   One long-running process: Engine boot (advisory writer lock + recovery
   replay) → cycles of open-execution reconciliation (the online path's
   stuck thresholds and re-read gaps make later cycles the delayed-reread
   schedule), interval-scheduled orphan sweeps with overlap windows,
   per-cycle operational gauges, and a freshness health file (the
   liveness-probe pattern for non-HTTP workers). SIGTERM/SIGINT stop
   claiming, finish the cycle, close, exit 0. A second worker is refused by
   the same lock — the single-writer invariant is enforced, not weakened.
2. **The multi-worker graduation is DESIGNED, not implemented**: a
   `scope_leases` table claimed with `FOR UPDATE SKIP LOCKED` (short claim
   transactions), heartbeat column + rescuer sweep, and an epoch column
   incremented on every (re)claim with **every ledger transition fenced by
   `WHERE epoch = $mine`** — the fencing the surveyed queues omit.
   Implementing it reopens ADR-002 (multi-writer) and therefore waits for
   that human ratification; this ADR records the design so the reopen is a
   decision, not a research project.
3. **Observability catalog extension** (RFC-002 §11 mechanism): stable,
   low-cardinality `worker.*` events (started/cycle/completed/
   stop_requested/stopped/reconcile_error/sweep_error); `worker.cycle`
   carries the gauges (open_executions, ambiguous_executions,
   oldest_open_age_s, open_findings, adjudicated, escalated, duration_ms).
   Names map 1:1 onto OTel conventions if telemetry returns post-M8; the
   ratified v0.1 no-OTel cut stands.
4. **Provider-adapter framework + two DRAFT adapters.** A shared HTTPS
   transport (`adapters/httpapi.py`) enforcing the RFC-002 §10 wire
   discipline (one call = one attempt; drops → LOST; deadline → TIMEOUT;
   statuses returned for declaration-cited classification), plus
   `StripeC1Adapter` and `EasyPostC2Adapter`: credential-gated (env-var
   NAME from config, value from environment only; sandbox/test key prefixes
   enforced — a live-mode key is refused at construction), version-pinned
   headers, declaration drafts with citations and `evidence_quality: EI`,
   synthetic-transport test suites (28 tests), and explicit DRAFT wording:
   **no live call has ever been made**. Live use waits on ADR-0010
   (Stripe pin — research recommends a full dated version), ADR-0012 (C2
   selection — EasyPost implemented as the recorded fallback; Shopify's
   auth/ToS questions stay human spikes), credentials, and ToS review.
5. **Independent baseline verdict: Temporal, at Stage-B.** The research
   verdict is recorded: Temporal is the one credential-free, MIT, single-
   binary runtime whose harness integration reproduces its own documented
   recommendation verbatim (activity + retries + idempotency key). Adding
   the `temporal-b5` arm is a Stage-B operationalization item (the §0
   checklist's "every baseline concretely operationalized") — not
   implemented pre-freeze because baseline arms bind into the frozen plan;
   the file-journal B5 remains the in-family stand-in with its equivalence
   boundary documented in its spec deviations. Restate (BSL server) and
   DBOS (in-process, same architecture class) are rejected as independent
   baselines, with reopen conditions.

## Alternatives

Per-effect row claiming (rejected: per-scope serialization must be
structural); expiry-only rescue without fencing (rejected: tolerates
duplicate execution — the exact failure Irrevon measures); implementing
multi-worker now (rejected: reopens ratified ADR-002 without the human);
an HTTP health server inside the worker (rejected for v1: freshness file +
`irrevon serve` cover liveness/readiness without a second listener);
Shopify-first C2 adapter (rejected pre-spike: offline-token and
benchmarking-ToS questions are blocking and human-owned).

## Consequences

Operators get a deployable service loop with documented probes and
shutdown semantics (docs/operations.md); provider adapters become a
reviewed skeleton the ADR-0010/0012 spikes fill in rather than green-field
work; the config surface (`[adapters.<id>] kind/credentials`) carries
names, never secrets. Conformance tests: tests/integration/test_worker.py
(settle + health, writer-lock exclusion, SIGTERM grace),
tests/adapters/test_provider_adapters.py (classification tables,
credential gating, pagination, declared query boundaries).

## Risks

The worker's reconcile pass is O(open executions) per cycle — acceptable
single-writer; the lease design addresses scale-out when ratified.
Provider declarations are research-grade (`EI`) until spikes contract-test
them; the schema and adapters make that status explicit rather than
implying verification.

## Reopen trigger

A multi-writer deployment need (activates decision 2 via ADR-002's reopen
path); ADR-0010/0012 ratification (promotes the draft adapters to spike
targets); Stage-B baseline operationalization (activates the Temporal
arm); Restate's BSL conversion date or a DBOS architectural change
(re-evaluates the baseline rejections).
