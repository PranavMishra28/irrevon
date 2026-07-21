---
id: ADR-0014
title: Outbound license and contributor-governance posture
status: open
date: 2026-07-20
supersedes: —
---

## Context

The master doc assumes Apache-2.0 (§10, §15/M2). That assumption is treated here as a
**leaning to be validated at the public-release gate**, not a closed decision — the grant only
becomes active at first public release, so nothing is gained by closing earlier, and the
one-way doors below are real. This ADR is the decision record; [../../LICENSING.md](../../LICENSING.md)
is the short posture notice. This is research synthesis, not legal advice.

Forces (from the master doc): benchmark neutrality is the #1 asset (§17); the adoption
goal requires zero legal friction for the project's primary audience (§14.1); the
commercial path is weak, optional, and G0-gated (§3.2/§3.3/§5.3); no revenue-bearing
activity is permitted until external clearances (§13).

### The legal mechanics that constrain the choice `[VF]`

- **Open source cannot prohibit commercial use** (OSD criteria 1/5/6). "Free for
  non-commercial use" licenses are by definition source-available, not open source. Copyleft
  is the only OSD-compatible mechanism that burdens commercial free-riders.
- **Genuine dual licensing requires rights over 100% of the codebase**: sole authorship,
  assignment, or a CLA with a sublicensing grant. Without one, a single outside copyleft
  contribution can veto any later relicensing (why Linux can never leave GPLv2).
- **Permissive inbound ≈ CLA for relicensing power**: an MIT/Apache inbound contribution may
  be sublicensed into differently-licensed future versions — how Redis relicensed a BSD
  codebase with 700+ contributors and no CLA (2024).
- **Relicensing is prospective only**: published versions remain available under their
  license forever (hence OpenSearch, OpenTofu, Valkey).
- **DCO vs CLA:** DCO (`Signed-off-by`) adds per-commit provenance attestation at near-zero
  friction and grants nothing beyond inbound=outbound. A CLA grants relicensing power but is
  now widely read as "relicensing reserved" — a costly signal for a project whose pitch is
  neutrality.

### One-way doors

1. **First public release under a license** — the grant on published versions is irrevocable.
   Too-permissive is effectively permanent for shipped code; too-restrictive is recoverable
   (relaxing later is safe and applauded).
2. **First outside contribution accepted** — no longer sole owner; permissive outbound
   preserves freedom anyway, copyleft-without-CLA forecloses dual licensing.
3. **Publishing publicly with no license** — all rights reserved destroys adoption, and PRs
   against an unlicensed repo have no inbound license basis. Never accept contributions in
   that state.
4. **Dependency entanglement** — keep dependencies permissive-only until this closes.

### Precedents (what relicensing actually costs) `[VF]`

| Project | Move | Outcome |
|---|---|---|
| MongoDB (2018) | AGPL→SSPL (CLA-backed) | OSI rejection; distro drops; AWS shipped a compatible API instead of forking |
| Elastic (2021→2024) | Apache-2.0→SSPL/ELv2, then +AGPL back | AWS forked → OpenSearch took real share; the CLA was the enabling "loophole" |
| HashiCorp (2023) | MPL→BSL (CLA-backed) | OpenTofu fork in 41 days under Linux Foundation |
| Redis (2024→2025) | BSD→RSAL/SSPL, then +AGPL back | Valkey fork within weeks; clouds defaulted to it; reversal judged too late |
| Sentry | BSD→BSL→authored FSL (2-yr conversion) | Mildest backlash; their default for new projects remains Apache-2.0 |

Lessons: relicensing restrictive-ward is always lawful with the right inbound rights and
always punished; permissive-ward is safe. For a **benchmark**, shipping restrictive even
temporarily forfeits the neutrality claim during the exact window credibility is built.

### Benchmark-specific norms `[VF]`

Code-centric agent benchmarks ship a single permissive license over harness and fixtures
(SWE-bench: MIT; τ-bench: MIT; AgentBench/HELM/BIG-bench: Apache-2.0). Separate data
licensing (CC-BY-4.0) is the norm only for large standalone corpora; Detent's fixtures are
self-generated synthetic data, removing the usual reason to split — though a standalone
HuggingFace fixture release with Croissant metadata would take CC-BY-4.0 (never apply CC
licenses to the harness code). RAIL-style behavioral-use licenses: checked and dismissed (no
model weights released; use restrictions would break OSD compliance and neutrality). The
held-out fault-seed split is deliberately unpublished and stays all-rights-reserved
permanently. Benchmark-integrity protection is a **trademark/name-control problem** (what may
be called a "DetentBench result"), not a license problem.

## Decision

**OPEN — decide at the public-release gate** (execution-plan, gate item 3; human queue item 7).

Recommended path `[EI]` (~85% confidence, consistent with the master doc's assumption;
revised 2026-07-21 — DCO tooling correction, relicensing-claim correction per the validity
review, interim wording updated for the now-public repository):

- **Outbound:** Apache-2.0 for all code and in-repo fixtures (engine, harness, adapters).
  Rationale against the evaluation criteria: matches the dominant benchmark norm
  (AgentBench/HELM/BIG-bench Apache-2.0; SWE-bench/τ-bench MIT); the §3 explicit patent
  grant + defensive termination lowers enterprise legal-review friction (MIT's patent
  silence is the runner-up's only deficit); proprietary embedding is the adoption path,
  not a leak; hosting risk is accepted as near-zero pre-G0.
- **Data/docs:** CC-BY-4.0 for standalone dataset artifacts (e.g. a fixture release with
  Croissant metadata) and docs/preprint. Never apply CC licenses to code. The held-out
  fault-seed split is never published and never licensed.
- **Inbound (once contributions open):** inbound=outbound plus **DCO sign-off, enforced**
  via GitHub's native required-signoff setting **plus a maintained DCO status check
  required on the default branch** (the status check is the enforcement control; the
  probot DCO app is unmaintained as of 2026 and must not be the mechanism). **No CLA** —
  adopt one only if genuine dual licensing is ever decided (requires G0 + external
  clearances + a recorded reversal of the neutrality posture in a superseding ADR).
- **Relicensing honesty (correction):** published versions remain under their license
  forever, and incompatible relicensing of outside contributions may require contributor
  consent absent a CLA/assignment — permissive inbound eases but does not unconditionally
  guarantee relicensing of combined works. No claim to the contrary is made.
- **Neutrality enforcement is name control, not license terms:** what may be called a
  "DetentBench result" is governed by a conformance policy under the (screened) name.
- **Interim (now):** the repository is publicly readable but unlicensed — all rights
  reserved; no contributions accepted; dependencies permissive-only. LICENSING.md carries
  the public-facing notice.

## Alternatives

- **MIT** — equal adoption ceiling, no patent grant; viable runner-up.
- **MPL-2.0 / LGPL** — file-level copyleft buys nothing for a harness; unusual signal.
- **GPL/AGPL (± dual license)** — kills lab/vendor CI adoption (blanket AGPL bans); optimizes
  the ~30% commercial branch at heavy cost to the 70% OSS branch.
- **BSL/FSL/ELv2/SSPL** — protects revenue that doesn't exist; fatal to the neutral-benchmark
  claim.
- **Publish unlicensed** — worst state; destroys adoption and inbound provenance.

## Consequences

Open-core remains fully available without CLAs (the G0-gated product would be new, separate
code). Ordered actions before accepting any outside contribution: (1) name screen passed
(P2); (2) this ADR closed by the human; (3) LICENSE (Apache-2.0) + NOTICE landed — a
released repository must never exist in an unlicensed state; (4) CONTRIBUTING.md published
(inbound=outbound, DCO, no CLA, pre-1.0 large-contribution policy); (5) DCO enforcement
live before the first external PR (required-signoff setting + required DCO status check);
(6) rulesets requiring the DCO check and review before merge; (7) dependency policy in CI:
permissive-only licenses. At first release the repository must also record the copyright
holder's legal name in LICENSE/NOTICE ("the repository owner" is not a valid public
copyright notice) and replace LICENSING.md with the standard LICENSE/CONTRIBUTING pair.

## Risks

If a deep-pocketed party ever hosts a commercial Detent, permissive licensing offers no
recourse — accepted: that scenario is the G0 world where a deliberate (and, per precedent,
costly) restriction decision for future versions could still be taken.

## Reopen trigger

G0 evidence gate satisfied; a funded competitor commercializes a hosted Detent; industry
consensus on benchmark/data licensing shifts materially; counsel or the external-clearance
review contradicts a premise above; the chosen DCO enforcement mechanism becomes
unmaintained (re-verify at release).
