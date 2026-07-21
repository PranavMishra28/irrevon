# DetentBench Preregistration Plan

> **STATUS: DRAFT — NOTHING IN THIS DOCUMENT IS FROZEN.**
> No section carries integrity weight until it is explicitly marked FROZEN through the §0
> procedure. Drafting hypotheses early is deliberate: they must demonstrably predate every
> observation. No benchmark run, sandbox spike, or fault trial may occur before the Stage-A
> freeze (execution-plan P3).

## 0. Freeze status and integrity

- **Version:** draft-1 · **Frozen:** NO (neither stage)
- **Two-stage design** (amendment AM-13, [review-queue.md](review-queue.md)):
  - **Stage A — design registration** (at P3, before any sandbox observation): §1 hypotheses,
    §2 matrix, §4 metrics, §5 analysis rules, §6 invalid-run rules, and the falsification
    criterion freeze. Stage A names no sandbox and hashes no artifacts, so it can freeze
    before the spikes that would otherwise contaminate it.
  - **Stage B — execution registration** (before any M7 confirmatory run): Stage A unchanged +
    §3 operationalizations (adapters, B5 configuration), artifact hashes, environment pins,
    and the sealed holdout hash. Only Stage B governs confirmatory claims; Stage A proves the
    hypotheses predate all tooling choices.
- **Stamping method (executed at freeze time, NOT now):** canonical file tree → SHA-256 of a
  deterministic archive → commit → **signed git tag** → **OpenTimestamps** stamp of the tag →
  **OSF registration** of the same document + hash. The signed tag binds plan↔repo; OTS makes
  backdating cryptographically implausible; OSF is the community-legible anchor.
- **Amendment policy:** frozen content is append-only. Amendments are numbered, individually
  hash-stamped, and must state what data (if any) had been observed before the amendment.
- **Freeze-preconditions checklist** (all must hold before the named stage freezes):
  - [ ] Stage A: review-queue amendments touching §8 of the master doc (AM-7, AM-13, AM-14)
        ratified or rejected by the human.
  - [ ] Stage A: statistical inference rules pinned (§5, including the equivalence procedure).
  - [ ] Stage B: C2 sandbox selected ([ADR-0012](decisions/0012-c2-sandbox.md) closed).
  - [ ] Stage B: Stripe version pinned ([ADR-0010](decisions/0010-stripe-api-version.md) closed).
  - [ ] Stage B: B5 concretely operationalized (which durable-execution runtime, version,
        configuration — "Temporal-like" is not preregisterable).
  - [ ] Stage B: frozen artifacts exist and are hashed — re-synthesis variant set (generated,
        human-spot-checked, labeled), workload seeds, fault schedules, sealed holdout split.
  - [ ] Stage B: environment pinning mechanism chosen (container base + digest procedure).
  - [ ] Stage B: capability declarations drafted for the chosen sandboxes (they define what
        "read-back" and "confirmed absent" mean per destination).

## 1. Research questions and hypotheses (from master doc §1.2, §8.6)

- **H1 (primary, directional):** on C2 destinations, R (Detent) shows a statistically
  significant, large reduction in duplicate-, orphaned-, and lost-legitimate-effect rates vs
  the **strongest baseline** — defined as the better-performing of B5 and the composite
  **B5+B3+B6** (amendment AM-7: a competent engineer's real-world best effort must be the
  primary comparison, or the claim silently shrinks) — across ≥5 seeds.
- **H0-C1 (pre-committed null):** on C1 destinations, R shows NO advantage over native
  idempotency (B4/B5) on duplicate rate. This null is reported as prominently as H1.
- **H-C3 (impossibility):** on C3 destinations, every method including R fails to detect
  lost/orphaned effects; the boundary is documented, not excused.
- **H4:** R's false-suppression rate ≤ B1's, and R reduces unresolved-ambiguous rate and
  human-review burden across tiers.
- **Falsification criterion** (per §8.6, with AM-14): if the strongest baseline is
  statistically **equivalent** to R on the C2 primary metrics — equivalence established by
  TOST against a pre-specified margin (§5), not CI overlap — Detent is unnecessary and the
  project is reframed as a teaching artifact (§14 kill). The benchmark is explicitly not
  designed so the system must win.
- **Confirmatory vs exploratory:** anything not listed above is exploratory and will be
  labeled as such.

## 2. Experimental design (the matrix)

Factors, per master doc §8.4:

- **Faults (7):** crash-before-persist · crash-after-effect-before-response · response-lost ·
  retry storm · semantic re-synthesis (frozen variants) · stale authorization · branch
  cancellation.
- **Effect classes (4):** idempotent · reversible · compensable · irreversible.
- **Capability tiers:** C1, C2, C3 — adapters named at Stage B.
- **Baselines:** B0–B7 + R per §8.3, plus the composite **B5+B3+B6** (AM-7). B7 receives the
  same model/budget as R's advisory classifier (LLM-budget parity) so the comparison is not
  compute-confounded.
- Baselines are **never weakened** (§8.3). Each baseline's exact operationalization is a
  Stage-B item.
- Cells excluded a priori (with reasons) are enumerated at Stage A freeze; e.g.
  fault×tier combinations that are undefined by construction. `[OPEN — enumerate before
  Stage-A freeze]`

## 3. Oracle and fixtures (per §8.2 — operationalized at Stage B)

Fixtures are the oracle: seeded workloads with known true intent identity; re-synthesis
variants pre-generated once, human-spot-checked, frozen, labeled same-intent/new-intent;
seeded fault schedules injected **client-side** against real destinations (destination-internal
failures cannot be induced — the benchmark tests the client/contract boundary and says so);
post-run destination read-back closes the loop for C1/C2; C3 cells score against fixture truth
only and are reported as such. Exact generation procedures, seed lists, and the variant-set
content hash are Stage-B artifacts.

## 4. Metrics (formulas with fixed denominators, per §8.4)

| Metric | Definition |
|---|---|
| Duplicate-effect rate | duplicates / dispatched |
| Orphaned-effect rate | destination effects without ledger intent / total destination effects |
| Lost-legitimate-effect rate | intended-but-absent / intended |
| Unresolved-ambiguous rate | AMBIGUOUS unresolved at run end / dispatched |
| False-reconciliation rate | incorrect classifications / classifications |
| False-suppression rate | legitimate effects blocked / legitimate |
| Precision / recall | vs oracle, per classification |
| Human-review rate & mean time | escalations / effects; wall-clock per escalation |
| Time-to-detect | dispatch→finding interval |
| Compensation correctness | correct compensations / compensations attempted |

Floors and ceilings: B0 is the floor; oracle-perfect is the ceiling. Interpretation note
(BetterBench design criterion): scores measure **client-side reconciliation capability against
declared destination contracts under injected faults** — they say nothing about destination
reliability, model quality, or end-to-end task success, and must not be quoted as such.

## 5. Statistical analysis plan

- ≥5 seeds per cell; seed list or derivation rule frozen at Stage B.
- Report means with 95% bootstrap percentile CIs over seeds and a pre-specified effect-size
  measure. `[OPEN — pin exact CI method and effect-size measure before Stage-A freeze]`
- **Superiority rule** (H1) and **equivalence rule** (falsification): equivalence via TOST
  with a pre-declared margin per metric. `[OPEN — margins must be pinned before Stage-A
  freeze; this is amendment AM-14 against master doc §8.6's "overlapping CIs" wording]`
- Multiple-comparison handling across cells: `[OPEN — pre-specify before Stage-A freeze]`.
- Every executed cell is reported; no post-hoc cell selection.

## 6. Invalid-run rules (per §12.2, fixed pre-run)

A run is INVALID iff any of: missing evidence artifacts (logs, ledger export, destination
read-back, environment manifest); fixture-reset verification failure; residual sandbox
effects after cleanup; seed mismatch vs plan. INVALID runs are **retained and marked, never
deleted**, and INVALID is not an exclusion lever — the rules above are exhaustive and fixed
here, pre-run.

## 7. Private held-out fault-seed split (per §8.1)

- **The held-out seeds never enter this repository, any agent context, or any committed
  file.** Only the sealed split's SHA-256 commitment hash enters the frozen Stage-B record.
- Storage location is decided at Stage B. Options under consideration: (a) encrypted archive
  on personal offline storage with the hash committed; (b) sealed object in a personal cloud
  bucket with versioning locked; (c) printed/escrowed seed material for maximal air-gap.
  `[OPEN — decide at Stage B]`
- Generation procedure and public/dev vs held-out proportion: Stage-B items. The dev split is
  usable for development; the held-out split is run **once**, at M7, and reported regardless
  of outcome. Unsealing condition and date are recorded at Stage B.

## 8. Run procedure, environment, and artifact homes

Per §12.2: tagged commit + environment manifest → verified fixture reset → single `RUN_SEED`
from the plan → execute → capture evidence (logs, ledger export, destination read-back,
manifest) or the run is INVALID → cleanup and verify no residual sandbox effects.
Second-machine reproduction; independent recomputation of a random 10% of cells before any
public claim (M7 gate).

**Artifact home policy** (declared now so nothing lands ad hoc; created when they exist):

| Artifact class | Future home |
|---|---|
| Frozen registration records (Stage A/B) + timestamp proofs | `docs/registrations/stage-a-v1/`, `stage-b-v1/` (append-only trees) |
| Amendments to frozen content | `docs/registrations/amendments/` (numbered, stamped) |
| Run manifests, evidence bundles, results (incl. INVALID) | `bench/runs/` (append-only; exact schemas are Stage-B artifacts) |
| Fixtures, frozen variants, fault schedules | `bench/fixtures/` (content-hashed) |
| Held-out split | **never in-repo** (§7) |

## 9. Reporting commitments

Null results (H0-C1) reported with equal prominence to any win. Publish threshold per master
doc §8.7: significant, large C2 reduction by R over the strongest baseline with tight CIs, a
clean C1 null, and a documented C3 boundary, reproducible from tagged commits + the private
split. Venue path: arXiv preprint → agents/reliability workshop → NeurIPS D&B track.
BetterBench self-score, Datasheets for Datasets documentation, and Croissant metadata ship
with results.

## 10. Deviations register

Empty at freeze; append-only thereafter.
