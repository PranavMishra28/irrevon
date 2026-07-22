---
id: ADR-0032
title: Causal effect histories, capability conformance verification, and oracle attribution hardening
status: proposed
date: 2026-07-22
supersedes: —
---

## Context

The owner's follow-on directive (2026-07-22) ordered a hostile audit of the
PR-11 benchmark foundation and adoption of the strongest defensible
contributions. Independent research tracks (history checking / formal
methods; protocol effect semantics; evaluation awareness; production
incidents) surfaced three weaknesses worth fixing now and a positioning
decision worth recording:

1. **Attribution fragility.** The oracle attributed destination effects by
   dispatched-payload digest. Real APIs normalize/enrich stored
   representations, so digest-only attribution breaks exactly where the
   benchmark claims validity (the audit's "payload-digest attribution under
   API normalization" item).
2. **Single-oracle scoring.** Per-trial final-state counting cannot express
   history-level facts (effect-after-cancellation, authority-at-dispatch,
   claim contradictions) and has no independent check on its own arithmetic.
   Prior art: Jepsen models histories as invoke/ok/fail/info operation logs;
   Elle (Kingsbury & Alvaro, VLDB'21) achieves polynomial-time anomaly
   checking by DESIGNING workloads for recoverability (unique written
   values) `[VF]`; FORGE/PCAS (arXiv 2602.16708) independently built
   runtime causal-graph checking of agent tool calls in 2026 `[VF]`.
3. **Self-asserted capability declarations.** MCP tool annotations
   (readOnlyHint/destructiveHint/idempotentHint, spec rev 2025-03-26) are
   explicitly untrusted hints; A2A leaves message idempotency as "MAY"; the
   IETF Idempotency-Key draft expired April 2026 unstandardized; OpenAPI has
   no effect semantics `[VF]`. Every ecosystem has advisory booleans; none
   has verified, parameterized recovery semantics.

## Decision

1. **Causal effect histories + checker** (`irrevon.bench.history`,
   `irrevonbench/history/v1`). Every run compiles a history — client events
   per trial in arm-action order, destination effects in the destination's
   authoritative request order — and a checker verifies eight named,
   linear-time behavioral invariants (H1 duplicate-effect, H2 orphan, H3
   lost-legitimate, H4 effect-after-cancellation, H5 unauthorized-effect,
   H6 false-suppression, H7 claim-contradiction, H8
   effect-despite-pre-persist-crash). Lineage credited explicitly: the
   history discipline follows jepsen.history; digest attribution is Elle's
   recoverability applied to external side effects. The narrow novelty
   claim, per the research tribunal: the combination of (a) the
   destination's authoritative log as ground truth, (b) irreversibility-
   domain invariants, and (c) benchmark-time offline checking under
   injected faults — no found system combines all three (FORGE is runtime
   client-side enforcement; τ-bench/Agent-Diff check end state only).
2. **The differential guard.** The §4 metric pipeline (read-back counting)
   and the history checker are two independent oracles; the runner requires
   their answers to be EQUAL per run. Divergence is finalized
   harness-INVALID ("independently proven harness corruption", §6). A
   metric bug that under-reports duplicates — the classic favorable-
   measurement failure — is now mechanically caught
   (tests/bench/test_history.py pins both directions).
3. **Diagnostics stay diagnostics.** H4/H5/H8 exceed the preregistration §4
   metric table. They are reported per run in the result's `history` block
   and NEVER pooled into §4 metrics or confirmatory analysis: adding a
   confirmatory metric is a preregistration change, not a harness change.
4. **Attribution hardening.** Attribution is digest-primary with a
   stable-id-projection fallback over the destination's stored ground
   truth; ambiguous projections are DECLINED and counted
   (`ambiguous_attributions`), never guessed. Refdest gained an
   `enrichment_quirk` (normalized/enriched stored representations) that
   breaks digest-only attribution by design; under it, all 488 effects of a
   full-matrix smoke attributed via projection with every measured rate
   byte-identical to the plain run (the adversarial measurement analysis
   for this change; recorded in the PR). Dev fixture payloads now carry
   their business identifiers — which is also what real order-create
   payloads do.
5. **Capability conformance verification** (`irrevon.bench.conformance`,
   `irrevon bench conform`, format `irrevonbench/conformance/v1`).
   Empirical declared-vs-observed probes through the PUBLIC adapter surface
   only: idempotency replay semantics, query-by-client-ref/destination-ref,
   authoritative absence, list-enumeration completeness. Capabilities the
   declaration denies (and the adapter therefore never exercises) report
   `unverifiable`, never `match`. Differential tests prove drifted
   declarations are caught (C1-declaration-on-C2-destination ⇒ ignored-key
   mismatch — the wedge itself, observed empirically). This operationalizes
   master doc §12.1 row 5 ahead of M6 and is the Stage-B mechanism for
   "capability declarations drafted for the chosen sandboxes".
6. **Positioning: verification layer, not a competing standard.** The
   protocol research shows boolean effect vocabularies are well-trodden
   (WoT TD `safe`/`idempotent`, ALPS, MCP hints) and standalone semantics
   standards die (ALPS and the Idempotency-Key draft both expired). Irrevon
   keeps its JSON-Schema capability declaration as the internal contract
   and ships a documented mapping annex
   ([docs/effect-semantics-mappings.md](../effect-semantics-mappings.md))
   projecting it onto MCP, A2A, OpenAPI, HTTP/Idempotency-Key, and ACP —
   positioning the declaration + conformance verifier as the verification
   layer over existing advisory vocabularies. No new standard is proposed.

## Alternatives

- *Adopt/port Elle or jepsen.history directly* — rejected: Clojure tooling,
  transaction-isolation anomaly domain; the applicable ideas (history
  discipline, recoverability, poly-time invariants) are small and
  implemented natively with credit.
- *Runtime enforcement monitor* (FORGE's territory) — rejected: Irrevon's
  contribution is measurement; the engine's gate already IS the runtime
  control being measured.
- *Score arms BY history violations directly* — rejected for confirmatory
  use: §4 metrics are the preregistered constructs; the checker
  cross-checks them rather than replacing them pre-freeze.
- *TEE/ZK verifiable private evaluation* — rejected now: no production
  precedent for "zero-knowledge benchmarks"; hash commitments + custody
  (already in place for the holdout) are the current credible mechanism.
- *A new protocol-neutral effect-semantics standard* — rejected (decision 6).

## Consequences

Runs become self-auditing artifacts (history + verdict + cross-check in
every bundle); a whole class of favorable-measurement bugs becomes
build-breaking; adapter authors get a mechanical conformance gate before
benchmark use; enterprises get capability-drift detection against live
destinations at M4+. Cost: two more modules under the anti-cheating
import-linter boundary; history compilation adds negligible runtime (linear
in events). Conformance tests: tests/bench/test_history.py (counterexamples
per invariant + doctored-metric detection), test_conformance.py
(match/drift differentials), test_oracle_metrics.py (enrichment/ambiguity),
test_cli.py, test_runner.py (history artifacts + cross-check).

## Risks

The projection fallback requires payloads to carry stable-id values —
documented as a workload-design rule (Elle's recoverability analog); a
Stage-B workload violating it degrades to digest-only attribution with
ambiguity surfaced, never silent misattribution. H-invariant semantics
could drift from §4 definitions — the differential guard turns that drift
into INVALID runs rather than silent skew. The conformance prober cannot
verify denied capabilities through a declaration-driven adapter (recorded
per probe as `unverifiable`).

## Reopen trigger

Stage-B freeze (history/conformance formats become frozen artifacts);
first real-sandbox adapter at M4 (conformance probes against live APIs —
rate limits and retention will need probe budgets); any proposal to score
confirmatory metrics from history violations (requires a preregistration
amendment, never a harness edit).
