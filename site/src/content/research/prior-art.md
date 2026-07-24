---
title: "Prior art: what we did not invent"
date: "2026-07-21"
summary: "Irrevon stands on decades of work — outboxes, idempotency, sagas, durable execution, agent-effect staging, replay, and reconciliation. This is the dated survey and its narrow inference."
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
  crash resumes instead of restarts. The recorded demo uses a developmental
  file-journal operationalization of those retry semantics. It is not evidence
  about Temporal; a real Temporal comparator remains a Stage-B prerequisite.
- **Staged commit for agents** — Cordon and Atomix stage an agent's effects and gate
  their release; Atomix also ships an evaluation. Closest neighbors, credited as such.
- **Record-and-replay for agent calls** — ACRFence intercepts and replays tool calls;
  its measurement of re-synthesis defeating idempotency keys (a 12-framework survey
  finding none enforce exactly-once at the tool boundary) is the published evidence
  behind Irrevon's problem statement.
- **Financial reconciliation** — Formance, Modern Treasury: the mature practice of
  pairing internal ledgers against external statements. Irrevon's orphan sweep is that
  practice, generalized to agent effects.
- **Tool-fault benchmarks** — ToolMaze and Self-Healing Agentic Orchestrators
  evaluate replanning, timeouts, malformed arguments, retry loops, and verification
  under tool perturbations. They do not perform destination effect accounting, but
  they make broad claims that tool-failure benchmarking is absent untenable.

## Two impossibility results set the ceiling

A client cannot guarantee exactly-once external effects against an arbitrary
destination when the request outcome can be lost and the destination exposes
neither dependable deduplication nor authoritative read-back. The tier table
states which narrower guarantee each destination class supports. FLP is relevant
distributed-systems context, not itself an exactly-once-delivery theorem.

## The narrow novelty claim

As of this documented July 2026 survey, we did not identify a standalone,
preregistered benchmark that jointly evaluates irreversible agent effects across
destination capability tiers using destination-authoritative read-back and a
precommitted duplicate, orphan, lost, contradicted, and false-suppression
analysis. That is a literature-search inference, not a priority, patentability,
or scientific-result claim. Irrevon is a pre-freeze attempt to build the
combination; real-provider and confirmatory work has not occurred.

Primary adjacent sources include
[Atomix](https://arxiv.org/abs/2602.14849),
[ACRFence](https://arxiv.org/abs/2603.20625),
[Cordon](https://arxiv.org/abs/2606.17573),
[ToolMaze](https://arxiv.org/abs/2606.05806), and
[Self-Healing Agentic Orchestrators](https://arxiv.org/abs/2606.01416).
