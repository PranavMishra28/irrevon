---
title: "Preregistering a benchmark, including the result that would kill it"
date: "2026-07-21"
summary: "How IrrevonBench uses a two-stage freeze before live and confirmatory evidence, while disclosing synthetic development pilots and a falsification criterion that would declare the engine unnecessary."
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
carries integrity weight yet, and it is not pristine: synthetic S-REF harness and
fault-smoke pilots have occurred, including a 488-effect attribution-hardening
pilot. They are disclosed as permanently non-confirmatory engineering evidence. No
live-sandbox observation or confirmatory run has occurred. Stage A must precede the former
and Stage B the latter; each freeze is a deliberate, human act.

## Why preregister a systems benchmark at all

2026 made the failure mode hard to ignore: benchmark credibility collapsed publicly when
OpenAI stopped reporting SWE-bench Verified in February after an audit found gains
increasingly reflected training-time exposure, and retracted its SWE-bench Pro
recommendation in July after flagging roughly a quarter to a third of public tasks as
broken. A benchmark whose author also ships the system being measured starts with even
less benefit of the doubt.

Preregistration is the experimental sciences' answer, but the claim must match the record.
The current draft was exposed to synthetic mechanism observations, so it cannot claim that
the hypotheses predate every datum. The remaining separation is explicit: freeze the
hypotheses, metrics, analysis plan, and falsification rule before any **live-sandbox**
observation, then freeze operational details before any **confirmatory** run. The plan is
to make both acts tamper-visible with a signed tag, external timestamp, and OSF
registration of the same hash. Whether the developmental exposure requires a reset or
independent review before Stage A is an open human ruling, not a claim this post resolves.

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

There are no scientific or confirmatory results. There is no frozen document. There are
disclosed developmental S-REF pilot observations that can support only mechanism debugging,
never an efficacy or live-provider claim. The draft is rendered on this site with its
source hash, canonical in the repository, and a
[reproduction contract](/docs/benchmark-reproduction/) is published before the first
live-sandbox or confirmatory run. When the freeze happens, it will be visible: a signed tag,
an external timestamp, and a hash that this site will cite instead of paraphrase.

One exposure is acknowledged rather than hidden: publishing the design before running
it means others can front-run the benchmark. The preregistration records that tension
as an open item; the integrity of the eventual results was judged worth the risk.
