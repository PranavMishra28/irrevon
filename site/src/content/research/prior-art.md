---
title: "Prior art: what we did not invent"
date: "2026-07-21"
summary: "Irrevon stands on decades of work — the outbox pattern, idempotency keys, sagas, durable execution, staged commit for agents, record-and-replay, financial reconciliation. The credit table, and the narrow thing that is actually new."
badges: ["conceptual"]
claims:
  - prior-art-credited
  - novelty-boundary
  - no-exactly-once
  - resynthesis-defeats-keys
sources:
  - label: "Master document §4.2 (the canonical credit table)"
    url: "repo:docs/master-doc.md"
  - label: "How it works — mechanism and prior-art section"
    url: "/how-it-works/"
---

*As of July 2026; the project reconfirms this survey quarterly. Corrections are
welcome through the repository.*

A project about honest handling of irreversible actions should start by being honest
about its own lineage. Almost every mechanism in Irrevon has decades of prior art, and
the master document keeps the canonical credit table. This post is the narrative
version.

## The credit table

- **The transactional outbox pattern** — persist the intent in the same transaction as
  local state, dispatch afterward. Irrevon's persist-before-dispatch is this pattern's
  discipline applied at the agent tool boundary.
- **Idempotency keys** — Stripe's client keys and Kafka's exactly-once semantics made
  key-based deduplication an industry norm. Irrevon sends them wherever the destination
  honors them; the C1 tier exists precisely because native keys already solve that case.
- **Sagas and compensation** — the long-lived-transaction literature established that
  distributed rollback is a fiction and compensation is a new forward action. Irrevon's
  compensation-is-not-rollback stance is that result, restated with measurement.
- **Durable execution** — Temporal, DBOS, Restate, Inngest: journal the workflow so a
  crash resumes instead of restarts. The recorded B5 baseline leg *is* this stack at its
  strongest, which is why it is the primary comparator.
- **Staged commit for agents** — Cordon and Atomix stage an agent's effects and gate
  their release; Atomix also ships an evaluation. Closest neighbors, credited as such.
- **Record-and-replay for agent calls** — ACRFence intercepts and replays tool calls;
  its measurement of re-synthesis defeating idempotency keys (a 12-framework survey
  finding none enforce exactly-once at the tool boundary) is the published evidence
  behind Irrevon's problem statement.
- **Financial reconciliation** — Formance, Modern Treasury: the mature practice of
  pairing internal ledgers against external statements. Irrevon's orphan sweep is that
  practice, generalized to agent effects.

## Two impossibility results set the ceiling

No universal exactly-once delivery exists — Two Generals and FLP settled that. The
achievable target is at-least-once delivery plus idempotent *or reconciled* processing.
Anyone claiming more is selling something; the tier table exists to say precisely which
guarantee each destination class supports.

## The narrow novelty claim

What is defensibly new is a combination and its measurement, not a mechanism: a
fault-injection benchmark drafted for preregistration for irreversible agent effects against real API
contracts with a destination read-back oracle — and reconciliation keyed on the
destination's authoritative-status query for C2 destinations. Even that claim is
deliberately narrowed in the master document's amendment log, because MAS-FIRE and
Atomix's evaluation exist. If the benchmark shows the conventional composite matches
the engine, the pre-committed conclusion is that the combination was unnecessary too.
