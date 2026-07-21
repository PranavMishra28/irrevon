# Execution plan — pre-implementation phases

The single roadmap home. Phases P0–P8 cover everything that can happen before implementation;
they feed the master doc's milestones M1–M10 ([master-doc.md](master-doc.md) §15), which remain
canonical for the implementation era. Owner "human" means the step cannot be delegated to an
agent; "agent" means an agent executes it as a bounded task from `tasks/` with human review.

Ordering rationale: **Stage-A preregistration freeze (P3) comes before any
sandbox spike (P4/P5).** A preregistration only has integrity value if the hypotheses,
metrics, and falsification criterion demonstrably predate every observation — and test-mode
API pokes are observations. This ordering was a reviewer-identified blocker against an earlier
draft plan that ran the spikes first.

| # | Phase | Gate (must hold before starting) | Exit criterion | Owner |
|---|---|---|---|---|
| P0 | Scaffold (this commit) | — | Tree in place; `make check` green; master doc moved byte-identical and hash-pinned | agent |
| P1 | Clearances + environment migration | — | (a) external clearances requested in writing (master doc §13; details tracked privately); (b) development-environment review item DE-1 closed (review-queue §3); (c) repo-scoped fine-grained PAT in use | human |
| P2 | Name screen ("Irrevon") | — | Registry screen recorded and name adopted 2026-07-21 ([ADR-0023](decisions/0023-rename-to-irrevon.md), superseding ADR-011); the counsel trademark clearance remains open pre-release | human (agent-assisted searches) |
| P3 | Preregistration Stage-A freeze | P1(b) complete; review-queue amendments affecting §8 ratified or rejected | Stage-A sections of [benchmark-preregistration.md](benchmark-preregistration.md) frozen: signed tag + external timestamp; freeze recorded in the document's §0 | human (agent drafts) |
| P4 | C2 sandbox spike | P3 done (spike generates observations) | [ADR-0012](decisions/0012-c2-sandbox.md) closed: sandbox chosen after Twilio-persistence and Amadeus-list checks | agent + human ratify |
| P5 | Stripe API version spike | P3 done | [ADR-0010](decisions/0010-stripe-api-version.md) closed: v1/v2 semantics pinned for the endpoints the adapter touches | agent + human ratify |
| P6 | Language/stack spike (T-000) | — (parallel with P4/P5) | **Done 2026-07-21:** [ADR-0013](decisions/0013-implementation-language.md) ratified from [tasks/T-000](../tasks/T-000-language-stack-spike.md)'s proposal | agent + human ratify |
| P7 | Preregistration Stage-B additions | P4, P5 done; fixtures/artifacts exist and are hashed | Stage-B sections frozen (adapters, baseline operationalization, artifact hashes, sealed holdout hash) before any confirmatory run | human (agent drafts) |
| P8 | Hand-off to implementation (M2+) | P1 fully complete (hard gate: **P1 blocks all implementation**); ADR-0013 ratified | First code task (toolchain bootstrap) opened per master doc M2/M3 | human opens; agents execute |

## Gate notes

- **P1 is the true critical path.** No product code is written anywhere, and nothing is
  published from anywhere, until the environment is personal and the clearances are at least
  requested (publication additionally requires them granted — master doc §13). Details and
  status live in [review-queue.md](review-queue.md) section 3.
- **P3 before P4/P5** is deliberate and load-bearing (see rationale above). If a spike must
  run early for a hard external reason, Stage-A must freeze first anyway; record the deviation
  in the preregistration's amendment log.
- **P4 → P7 ordering:** Stage-B names concrete adapters, so it cannot freeze before the C2
  sandbox is chosen.
- ADR ratification is always human. Agents produce recommendation text and evidence; the
  status flip to `accepted` is the human's act.

## Mapping to master-doc milestones

- **M1 Freeze** = P2 + P3 (+ ADR-0000, already accepted) — with one amendment: the master
  doc's "benchmark plan preregistered and hash-stamped" at M1 is satisfied by the **Stage-A**
  freeze; the full execution registration is Stage-B (P7, before M7 runs). This two-stage
  resolution is amendment AM-13 in [review-queue.md](review-queue.md).
- **M2 Env** = P8 plus the master doc's M2 items (CI, local database, sandbox projects,
  runbook). CI design and workflows are in ([ci.md](ci.md) + `.github/workflows/`); the
  repo being public makes rulesets/branch protection, secret scanning + push protection,
  and CodeQL available at no cost — enabling them is a human settings act (owner checklist
  in [ci.md](ci.md)). Local `make check` + pre-commit remains the enforcement layer until
  required checks are configured.
- **M3–M10** proceed per master doc §15; P4/P5/P6 will already have closed the decisions M4
  depends on.

## Public-release gate (last, listed once)

The repository itself is public (owner decision 2026-07-21, final), after a ratified
sanitization pass over the tracked tree (amendment AM-16 in the review queue;
pre-sanitization wording persists in git history — the history question is a recorded,
owner-deferred item). **Releasing anything beyond the readable repository** — a package, a
release/tag with artifacts, a preprint, a demo, Pages — requires ALL of:

1. External clearances **granted in writing** (master doc §13).
2. Counsel trademark clearance of "Irrevon" completed (the registry screen is recorded and
   the name adopted per [ADR-0023](decisions/0023-rename-to-irrevon.md); counsel screening
   is the remaining half).
3. Licensing decision closed ([ADR-0014](decisions/0014-licensing.md)) with LICENSE/NOTICE
   and inbound policy in place.
4. Sanitization review of the release artifacts: tripword scan
   (`scripts/check-integrity.sh` with the local `.tripwords` list) plus a human read of
   every released artifact for personal or third-party-sensitive material.
5. Distribution mechanics per [ADR-0018](decisions/0018-distribution-model.md) (trusted
   publishing, immutable releases, signed tag).
6. Human sign-off. No agent ever performs a publication step.
