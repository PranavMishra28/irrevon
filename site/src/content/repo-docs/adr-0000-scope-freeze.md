---
title: "Freeze project scope — benchmark-first, C2-scoped, with binding non-goals"
sourcePath: "docs/decisions/0000-scope-freeze.md"
sourceSha256: "b9f3159eaa8476a5f84ac2ffaccb739e5991fffb4f2ddedc6a749bd6615a84ad"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0000"
  status: "accepted"
  date: "2026-07-20"
  supersedes: "—"
---

## Context

The master doc ([../master-doc.md](../master-doc.md)) — the human's own authoritative
document — already froze the technical question (§1.2), declared the non-goals binding
(§5.4), and fixed the benchmark-first, C2-scoped framing after adversarial revalidation
(§1.1, §1.3, ADR-009). M1 requires this freeze to be recorded as ADR-000. This ADR is a
faithful record of that existing decision, not a new one; it is recorded `accepted` on the
master doc's authority, with an explicit human countersign requested in
[../review-queue.md](../review-queue.md) section 3.

## Decision

The frozen scope is, verbatim by reference:

- **Technical question:** master doc §1.2 — duplicate/orphaned/lost effects under ambiguous
  irreversible actions, and how much a deterministic reconciler eliminates or surfaces
  without the agent's cooperation.
- **Framing:** benchmark-first; the reference engine is a baseline within the benchmark, not
  a product (§1.1, ADR-009). Scoped to C2; C1 null pre-committed; C3 demonstrated as an
  impossibility boundary.
- **Non-goals (binding, §5.4):** not a durable-execution runtime, auth layer, approval
  gateway, dashboard, or hosted SaaS; no billing; no universal exactly-once claim;
  compensation is not rollback; the LLM never holds sole authority over an irreversible
  action; not a payments/clearing protocol; no revenue-bearing activity until written
  immigration guidance permits it.

This freeze deliberately does **not** freeze open implementation choices: language
(ADR-0013), C2 sandbox (ADR-0012), Stripe version (ADR-0010), statistics margins
(preregistration §5), licensing (ADR-0014).

## Alternatives

- *Leave the freeze implicit in the master doc* — rejected: M1 explicitly requires ADR-000,
  and the freeze needs a countersignable artifact.
- *Re-litigate scope at scaffold time* — rejected: the master doc survived adversarial
  revalidation; reopening without new evidence burns the ~10 hrs/week on relitigation.

## Consequences

Agents may not add product requirements or expand scope; anything scope-shaped goes to the
review queue. Tasks citing this ADR can rely on §5.4 as a hard boundary.

## Risks

A frozen scope can ossify against genuinely new evidence. Mitigated by the reopen trigger
below and the quarterly competitor review (§14.2, O-3).

## Reopen trigger

An adopted competitor covers the C2 reconcile-by-query wedge (master doc §4.3 kill rule), or
the pre-committed falsification criterion fires at M7 (§8.6 → §14.3 reframe).
