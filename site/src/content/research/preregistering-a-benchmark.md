---
title: "Preregistering a benchmark, including the result that would kill it"
date: "2026-07-21"
summary: "How IrrevonBench borrows preregistration from the experimental sciences: hypotheses, metrics, and analysis frozen before any run — with a pre-committed falsification criterion that would declare the engine unnecessary."
badges: ["preregistered"]
claims:
  - prereg-draft-status
  - kill-criterion
  - baseline-ladder
  - c1-null-precommit
  - credibility-controls
  - stats-discipline
  - benchmark-crisis
  - stamping-planned
sources:
  - label: "IrrevonBench preregistration (DRAFT, rendered)"
    url: "/docs/reference/benchmark-preregistration/"
  - label: "Benchmark design — the narrative version"
    url: "/benchmark/"
---

The preregistration this post describes is a **draft**. Nothing is frozen, no section
carries integrity weight yet, and no benchmark run, sandbox spike, or fault trial may
occur before the Stage-A freeze — which is a deliberate, human act. That status is the
first thing the document itself says, and it should be the first thing this post says.

## Why preregister a systems benchmark at all

2026 made the failure mode hard to ignore: benchmark credibility collapsed publicly when
OpenAI stopped reporting SWE-bench Verified in February after an audit found gains
increasingly reflected training-time exposure, and retracted its SWE-bench Pro
recommendation in July after flagging roughly a quarter to a third of public tasks as
broken. A benchmark whose author also ships the system being measured starts with even
less benefit of the doubt.

Preregistration is the experimental sciences' answer, and it transfers: write down the
hypotheses, the metrics, the analysis plan, and — critically — the result that would
falsify the thesis, *before* any observation exists. Then freeze it where tampering
would be visible: the plan is to stamp the frozen document with a signed tag,
an external timestamp, and an OSF registration of the same hash. Two stages: a design
freeze before any sandbox observation, an execution freeze before any confirmatory run.

## The kill criterion, stated plainly

The pre-committed falsification criterion: if the strongest composite conventional
baseline is statistically equivalent to or better than Irrevon on every primary metric
of the confirmatory stratum — equivalence tested with TOST, with a worst-cell gate —
then Irrevon is unnecessary, and the project reframes as a teaching artifact. The
benchmark is explicitly not designed so the system must win.

Two more commitments cut the same way:

- **The baseline ladder is never weakened.** B0 through B7 plus R are preregistered;
  the preselected primary comparator is the composite B5+B3+B6, with B5 reported
  alongside — superiority must reject against both.
- **The C1 null is pre-committed.** On destinations with dependable native idempotency,
  Irrevon is expected to show *no* advantage on duplicate rate, and that null will be
  reported as prominently as any positive result.

## The discipline behind the numbers

Every published number is preregistered to arrive with its uncertainty and its
denominator: oracle-fixed, arm-independent metric denominators; at least five seeds per
cell (ten planned); means with confidence intervals and effect sizes, never point
estimates; every executed cell reported; INVALID runs retained and marked rather than
deleted. A sealed private holdout of fault seeds never enters the repository, so the
confirmatory stratum cannot have been tuned against its own test. Before any public
claim: a second-machine reproduction and independent recomputation of a random 10% of
cells.

The benchmark also self-scores against BetterBench's lifecycle criteria and ships
Datasheets-for-Datasets documentation and Croissant metadata — the credibility
apparatus is part of the deliverable, not an afterthought.

## What exists today, and what does not

There are no results. There is no frozen document. There is a draft anyone can read —
rendered on this site with its source hash, canonical in the repository — and a
[reproduction contract](/docs/benchmark-reproduction/) published before the first run
so the promise is inspectable in advance. When the freeze happens, it will be visible:
a signed tag, an external timestamp, and a hash that this site will cite instead of
paraphrase.

One exposure is acknowledged rather than hidden: publishing the design before running
it means others can front-run the benchmark. The preregistration records that tension
as an open item; the integrity of the eventual results was judged worth the risk.
