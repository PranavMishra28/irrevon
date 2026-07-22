---
title: "Outbound license and contributor-governance posture"
sourcePath: "docs/decisions/0014-licensing.md"
sourceSha256: "573a2ef22dba3ed1e87ce5f1ad01849a80157155171f0cbb8409441a647e72ca"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0014"
  status: "open"
  date: "2026-07-20 (analysis refreshed 2026-07-21 from the LIC-2 deep research)"
  supersedes: "—"
---

> **RESEARCH SYNTHESIS — NOT LEGAL ADVICE.** Consult a licensed attorney before adopting
> any license, filing any trademark application, or accepting any outside contribution.

## Context

The master doc assumes Apache-2.0 (§10, §15/M2). That assumption is treated here as a
**leaning to be validated at the public-release gate**, not a closed decision — the grant
only becomes active at first public release, so nothing is gained by closing earlier, and
the one-way doors below are real. This ADR is the decision record;
[../../LICENSING.md](../../LICENSING.md) is the short posture notice.

The 2026-07-21 refresh re-runs the analysis under the owner's revised stated priorities:
(1) nobody can "simply copy, fork, and run off with it" if the project becomes extremely
successful; (2) persistent attribution — "my imprint needs to still be there"; (3) map what
paid compliance / commercial licensing would involve later; (4) lawyer-worthy rigor.
Standing constraints are unchanged: benchmark neutrality is the #1 asset (§17), adoption is
required for the career signal (§14.1), and no revenue-bearing activity is permitted until
external clearances close (§13).

### The legal mechanics that constrain the choice `[VF]`

- **Open source cannot prohibit copying, forking, or commercial use** — the OSD requires
  every approved license to permit exactly those acts (OSD 1/3/5/6). Goal (1) as literally
  stated is purchasable only by source-available licensing, which forfeits the open-source
  claim entirely. There is no third option.
- **Attribution survives every fork under every candidate license**: MIT's notice clause,
  Apache-2.0 §4(c)–(d) (NOTICE-file reproduction), GPL/AGPL §4–§5 + §7(b), ELv2's
  notice-preservation term, CC-BY-4.0 §3(a). Stripping notices is infringement under all
  of them. File-level imprint (goal 2) is therefore already guaranteed everywhere.
- **What does not survive a fork is the name.** Every major relicensing fork kept the code
  and lost the name (OpenSearch, OpenTofu, Valkey, Iceweasel) — trademark law, not the code
  license, forced each rename. No code license grants the marks (Apache-2.0 §6 excludes
  them expressly). Trademark + conformance policy, not license restriction, is the
  strongest practical answer to the imprint goal.
- **Copyright never protects the idea** (17 U.S.C. §102(b)). The absorption worry (§4.3,
  §14.2) has a failure mode no license reaches: reimplementation of the (deliberately thin)
  reconcile-by-query logic from the published benchmark. Copyleft raises the cost of code
  absorption only.
- **Copyleft's true triggers are narrow** `[VF]`: GPL-3.0 §2 — internal use, including a
  frontier lab running the engine in CI with private modifications, creates zero
  obligations; AGPL-3.0 §13 bites only when a *modified* version is offered to *remote
  users*. "Paid compliance" for mere adopters is FUD — unmodified users owe nothing, ever.
  The real adoption cost is corporate policy, not law: Google's blanket AGPL ban covers
  even workstation installs, and permissively-licensed agent frameworks cannot hard-depend
  on a copyleft library.
- **Genuine dual licensing requires rights over 100% of the code**: sole authorship,
  assignment, or a CLA with a sublicensing grant. A single outside copyleft contribution
  without a CLA permanently vetoes relicensing of the touched code. Permissive inbound
  substitutes for a CLA for relicensing purposes (Redis 2024) but not for dual-licensing
  copyleft code.
- **Relicensing is prospective only**: published versions remain available under their
  license forever.
- **Enforcement reality for a solo owner** `[EI]`: copyright litigation is
  six-to-seven-figure and multi-year; the working tools are DMCA takedowns, community
  pressure, and copyleft's deterrent effect on compliance departments. Trademark
  enforcement (C&D letters, platform name disputes, UDRP) is the tractable lever, and
  *Planetary Motion v. Techsplosion* (11th Cir. 2001) holds that free distribution creates
  enforceable mark rights — no revenue needed, directly relevant to the §13 constraint.

### Goal → mechanism map `[EI]`

| Owner goal | Best mechanism | What the mechanism cannot do | Verdict |
|---|---|---|---|
| (1) "Can't copy, fork, and run off with it" | **Not achievable under open source** (OSD 1/3/5/6). Nearest OSD-compatible proxy: **AGPL on the engine** (forks/serving stay open). The full version requires source-available (BSL/FSL) at fatal cost to neutrality + career goals | Copyleft can't stop reimplementation of the idea (§102(b)), internal use, or unmodified hosting | Partial by design; buy the proxy, not the impossibility |
| (2) "My imprint still there" | **Trademark on Detent/DetentBench (+ logo) + conformance policy** (forks must rename) + **NOTICE-file attribution** (survives every fork under every license) + CC-BY on data | Nothing — this goal is fully achievable, cheaply | **Fully achievable; the real answer** |
| (3) Paid compliance / commercial licensing later | **Dual-license option on an AGPL engine** (needs unified engine ownership: CLA-or-no-outside-engine-PRs decision) + **open-core** (hosted service, adapters, support) + **trademark-based certification program** (SPEC/TPC/MLCommons model) | Nothing is sellable until G0 + external clearances; "paid compliance" for mere adopters is FUD | Preserve optionality now; transact later |
| (4) Lawyer-worthy rigor | Primary sources in the LIC-2 research file; counsel review of final license texts, trademark filing, CLA text if ever, entity question | — | Checklist in Consequences |
| Benchmark neutrality + adoption (§10/§17 — still product truth) | **Apache-2.0 harness/schemas/SDK**, pinned containers, preregistration, trademark-conformance | Conflicts with (1): every unit of restriction is paid for in adoption | The conflict to surface to the human |

### One-way doors

1. **First public release under a license** — the grant on published versions is
   irrevocable. Under the hybrid candidate this door is **per-component**. Too-permissive
   is effectively permanent for shipped code; too-restrictive is recoverable.
2. **First outside contribution accepted** — no longer sole owner. A first outside AGPL
   engine contribution without a CLA permanently forecloses dual-licensing of the touched
   code (consent/rewrite/removal only); the engine-CLA decision must precede the first
   engine PR.
3. **Publishing publicly with no license** — all rights reserved destroys adoption, and
   PRs against an unlicensed repo have no inbound license basis. Never accept
   contributions in that state.
4. **Dependency entanglement** — keep dependencies permissive-only until this closes.
5. **A bespoke GPL §7 "benchmark execution" exception**, once shipped, creates a
   nonstandard license permanently attached to released versions — never add one without
   counsel.
6. **Publishing a trademark policy** sets community expectations that are reputationally
   expensive to tighten later (Rust 2023 precedent); calibrate generously the first time.

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
Benchmark bodies (MLPerf, SPEC, TPC) police result integrity through trademark and
conformance policy over what may wear the name — never through the code license; MLPerf
*requires* open-source-licensed implementations `[VF]`.

### Name-screen dependency (blocks everything below) `[VF]`/`[OQ]`

The entire trademark/imprint strategy is contingent on the §13 name screen (review-queue
human item 4), which the FR3 identity research (2026-07-21) has now materially informed.
Collision findings, highest severity first:

1. **PyPI package `detent` is taken** (v1.2.0, "verification runtime that intercepts AI
   coding agent file writes… rolls back atomically") — nearly this project's exact
   conceptual space, and ADR-0013 chose Python, making the registry collision material.
2. **`digitaldrywood/detent`** (GitHub, Go, MIT) — active AI-agent dev-orchestration tool
   (76 releases as of 2026-07-19): same name, adjacent domain, same channel.
3. **DetentLabs (detentlabs.ai)** — web3 wallet security using the exact "clicks into its
   detent" safety metaphor, different ecosystem.

npm and crates.io `detent` are available; the GitHub user `detent` is taken. Items 1–2
plausibly meet ADR-0011's reopen trigger ("registry/trademark screen reveals a Detent
collision — fall back to a runner-up"). That determination is **human-only** (ADR-0011 is
frozen in master doc §11); the findings are recorded against review-queue item 4. The name
screen should now explicitly include a USPTO clearance search, because the trademark
strategy is load-bearing for the imprint goal.

## Decision

**OPEN — decide at the public-release gate** (execution-plan gate item 3; review-queue
human items 7 and 18). Two candidate postures; selection pending the owner's ratification
of the goal ranking (neutrality-first vs. protection-first). Counsel review precedes
closing. This is research synthesis, not legal advice.

**Candidate B (protection-first — hybrid) `[DD]`, primary iff the owner ratifies the
revised priority ranking:**

- Engine (the reference reconciliation engine, the "R" baseline): **AGPL-3.0-only**.
- Benchmark harness, JSON schemas, SDK/client, adapter interface: **Apache-2.0**.
- Standalone dataset/doc artifacts: **CC-BY-4.0**. Held-out fault-seed split: never
  published, never licensed.
- Names/logo: trademark + DetentBench conformance policy (what may be called a
  "DetentBench result"), modeled on MLPerf/SPEC practice; TRADEMARKS.md ships at first
  release.
- Inbound: DCO everywhere (enforced via required sign-off **plus a maintained required
  DCO status check** — the probot DCO app is unmaintained as of 2026 and must not be the
  mechanism). Engine contributions additionally gated by a pre-decided choice:
  engine-scoped CLA **or** no outside engine contributions (preserves dual-license
  optionality); harness/schemas/SDK take DCO-only contributions freely. No general CLA.
- Architectural invariant: the Apache-2.0 harness/SDK invoke the AGPL engine only at
  arm's length (subprocess/container/RPC); no library-import coupling. Nothing on the
  Apache side may depend on the engine.
- **Core trade-off, stated plainly:** the owner buys "engine forks stay open + a
  paid-exception path" and pays with a reproducibility asterisk on the headline R-vs-B5
  number at AGPL-banning organizations, an arm's-length architecture constraint, a
  permanent license-boundary maintenance cost, and a more complicated story. It does not
  stop a determined incumbent from reimplementing the reconcile logic.
- **Governance:** choosing B contradicts the master doc's standing Apache-2.0 assumption
  (§10, §15/M2) and therefore additionally requires a human-ratified review-queue
  amendment (extending AM-19) recording the priority change.

**Candidate A (neutrality-first — prior leaning), runner-up:** **Apache-2.0 for all code
and in-repo fixtures + CC-BY-4.0 data + the same trademark/conformance, NOTICE, and DCO
layers** made explicit and first-class. Choose this if the owner keeps the master doc's
goal ranking (neutrality ≫ career ≫ optional commercial) — it concedes code-level
absorption (recoverable for *future* versions post-G0, at documented reputational cost
per the precedents) and wins everything else. Under this ranking A wins the scoring
outright `[EI]`.

**Relicensing honesty (both candidates):** published versions remain under their license
forever, and incompatible relicensing of outside contributions may require contributor
consent absent a CLA/assignment. No claim to the contrary is made.

**Interim (now):** the repository is publicly readable but unlicensed — all rights
reserved; no contributions accepted; dependencies permissive-only; trademark filing
decision follows the name screen. LICENSING.md carries the public-facing notice.

## Alternatives

- **All-AGPL-3.0** — adds engine protection *and* poisons the harness/schemas/SDK: labs
  that can't run AGPL can't run the benchmark at all; the effect-contract registry can't
  become a standard. Strictly dominated by the hybrid on every criterion.
- **MIT (in place of Apache-2.0)** — equal adoption ceiling, no patent grant; viable
  runner-up within Candidate A only.
- **MPL-2.0 / LGPL** — weak copyleft delivers a fraction of the protection at a fraction
  of the adoption cost of AGPL; file-level copyleft is not an anti-absorption mechanism
  and the SaaS gap remains. Strictly dominated by A or B.
- **BSL-1.1 / FSL-1.1 / ELv2 / SSPL / PolyForm (source-available)** — the only
  instruments that genuinely deliver goal (1), and they cost the open-source label,
  benchmark neutrality, distro presence, and the career signal, to protect revenue that
  cannot lawfully exist yet (§13). If goal (1) is ever elevated to lexically-first after
  G0 evidence exists, FSL is the least-bad instrument in the family (2-year irrevocable
  Apache/MIT conversion, Sentry precedent).
- **Publish unlicensed permanently** — worst end-state; destroys adoption and inbound
  provenance. (Acceptable only as the current interim, with contributions closed.)

## Consequences — pre-contribution action list, ordered

Before accepting any outside contribution (and mostly before first release):

1. **Name screen (§13) including a USPTO clearance search** — blocks everything below;
   the FR3 collision findings above are its current evidence base.
2. **Owner ratifies the goal ranking** (review-queue item 18); if B, ratify the
   review-queue amendment superseding the master doc's Apache-2.0 assumption; close this
   ADR (human-only).
3. **Counsel review**: license split, trademark filing basis (§1(a) use vs §1(b)
   intent-to-use; IC 9/42), and the F-1 items flagged in the LIC-2 research file.
4. **First licensed release ships**: LICENSE file(s) per component, NOTICE (named
   copyright holder + attribution — "the repository owner" is not a valid public
   copyright notice), TRADEMARKS.md (nominative fair use + conformance rule),
   CONTRIBUTING.md (inbound=outbound, DCO required, engine contribution policy),
   per-artifact license table in README; LICENSING.md is replaced by the standard pair.
5. **DCO enforcement live** (required sign-off + required status check) before the first
   external PR; rulesets requiring the DCO check and review before merge.
6. **US copyright registration** of the released codebase (~$65) within 3 months of first
   publication (preserves statutory damages, 17 U.S.C. §412).
7. **USPTO trademark application(s)** for the screened name ($350/class; SOU $150/class
   if intent-to-use) — timing per counsel.
8. **Dependency-license policy in CI**: permissive-only (on the Apache side under B; no
   engine imports across the boundary).

Open-core remains fully available without CLAs under either candidate (the G0-gated
product would be new, separate code).

**Structural flag appended 2026-07-21 (legal-readiness review; this ADR is OPEN, so the
analysis may grow):** ADR-0018 ships **one** wheel containing engine and SDK/CLI, whose
modules import each other freely. A single PyPI artifact mixing AGPL and Apache code is
expressible (`License-Expression: AGPL-3.0-only AND Apache-2.0` + per-file SPDX) but
weakens the hybrid's point — Candidate B's arm's-length invariant ("no library-import
coupling; SDK talks to the engine across a process boundary") is **not satisfied** by the
current single-package layout. **Choosing B therefore forces either a package split
(contradicts ADR-0018 — needs a superseding ADR) or an in-package module firewall with
import-linter contracts + counsel sign-off.** Candidate A has no such cost. Recorded as
review-queue §3 item 24; decide together with items 7/18. No speculative packaging change
is made meanwhile — ADR-0018's single wheel ships as-is.

## Risks

If a deep-pocketed party ever hosts a commercial Detent, permissive licensing (Candidate
A) offers no recourse — accepted: that is the G0 world where a deliberate (and, per
precedent, costly) restriction decision for future versions could still be taken. Under
Candidate B, the reproducibility asterisk at AGPL-banning organizations lands on exactly
the frontier-lab audience the master doc targets, and every future engine/harness refactor
acquires a license dimension.

## Reopen trigger

G0 evidence gate satisfied; a funded competitor commercializes a hosted Detent; industry
consensus on benchmark/data licensing shifts materially; counsel or the external-clearance
review contradicts a premise above; the chosen DCO enforcement mechanism becomes
unmaintained (re-verify at release); the SFC v. Vizio verdict (trial begins 2026-08-10)
materially shifts copyleft enforceability expectations; the name screen fails for
Detent/DetentBench (the trademark strategy must restart under the fallback name —
ADR-0011's reopen trigger, tracked as review-queue item 4).
