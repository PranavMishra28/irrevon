# Review queue

Three lists a human must act on. **Nothing here is authoritative.** The master doc
([master-doc.md](master-doc.md)) remains the sole source of product truth until an amendment
below is explicitly ratified; ratification integrates the change into a new master-doc version
and re-pins the hash in `scripts/master-doc.sha256`. Agents append to this file; only humans
resolve items. The status annotations dated 2026-07-21 record the owner's written
ratifications of that date, applied by the integrator at the owner's direction during the
release-candidate reconciliation.

## 1. Master-doc amendments

Refinements surfaced by pre-scaffold research verification and the 2026-07 design reviews.
No fabricated citations were found in the master doc — every named paper, product, and
figure checked out against primary sources.

| # | Master doc location | Change | Source/evidence | Status |
|---|---|---|---|---|
| AM-1 | §4.1 | Narrow "no existing benchmark isolates these": MAS-FIRE (arXiv 2602.19843, semantic/coordination fault injection) and Atomix's eval (fault injection + irreversible-leakage counting on mocks) now exist. Rephrase to "no standalone, preregistered benchmark against real production API contracts with a destination read-back oracle." | Research verification vs arXiv, July 2026 `[VF]` | **RATIFIED 2026-07-21** (text integration pending) |
| AM-2 | §4.3 Atomix row | Update "in-memory dedup" (v1 limit) to the v2 claim: SQLite-backed single-process crash-safe dedup, unit-tested only, explicitly no distributed exactly-once. Differentiation unchanged. | Atomix v2, arXiv 2602.14849 `[VF]` | **RATIFIED 2026-07-21** (text integration pending) |
| AM-3 | §4.3 ACRFence row | Add strengthening fact: ACRFence's paper validates the attacks but does not implement the ACRFence mitigation itself — attack PoC only. | arXiv 2603.20625 `[VF]` | **RATIFIED 2026-07-21** (text integration pending) |
| AM-4 | §2.3 | Caveat the Anthropic figures: 73%/0.8% are model-classified estimates; Anthropic notes over-estimation of human involvement, so 73% is an upper bound. | Anthropic autonomy post `[VF]` | **RATIFIED 2026-07-21** (text integration pending) |
| AM-5 | §7.5 / ADR-010 | Scope ADR-010: Stripe v2 idempotency applies to the /v2 namespace only; PaymentIntents/Charges are v1 (24h, cached-error replay). Pin v1 semantics for payments-namespace endpoints. | Stripe API docs `[VF]` — carried into [decisions/0010-stripe-api-version.md](decisions/0010-stripe-api-version.md) | **RATIFIED 2026-07-21** |
| AM-6 | §7.5 C1 examples | Tag QuickBooks Online C1 as `[EI]` pending contract tests: a public SDK issue shows duplicates despite RequestId via the .NET SDK path. | intuit/QuickBooks-V3-DotNET-SDK#352 `[VF]` | **RATIFIED 2026-07-21** |
| AM-7 | §8.3/§8.6 | Add composite baseline **B5+B3+B6** to the preregistered plan; give B7 LLM-budget parity with R's advisory classifier. | Baseline-ladder gap analysis `[EI]` | **RATIFIED 2026-07-21 with validity-review correction:** the composite is the **preselected primary comparator** (no per-metric data-driven "strongest" selection, which would invalidate TOST coverage); B5 is reported alongside; superiority must reject against both. Corrected text is live in [benchmark-preregistration.md](benchmark-preregistration.md) §1/§5.3 |
| AM-8 | §5.2/§13 | Add sandbox-selection spike items: Twilio test creds may not persist queryable messages; Amadeus self-service has no list endpoint + session-scoped IDs. Recommend Shopify dev store primary / EasyPost fallback; note Shopify dev-store 5 orders/min cap. | API-doc verification `[VF/EI]` — carried into [decisions/0012-c2-sandbox.md](decisions/0012-c2-sandbox.md) | **RATIFIED 2026-07-21** |
| AM-9 | §7.3 CapabilityDeclaration | Add fields `client_ref_field` and `list_queryable` — they determine whether ORPHANED and LOST are detectable per destination. | Per-destination reconcile-hook survey `[EI]` — fields live in [../schemas/capability-declaration.schema.json](../schemas/capability-declaration.schema.json) | **RATIFIED 2026-07-21** |
| AM-10 | §4.2 | Credit the effect-class taxonomy {IDEMPOTENT, REVERSIBLE, COMPENSABLE, IRREVERSIBLE} to Revisable-by-Design (arXiv 2604.23283) and Gray 1978 (via Atomix). | arXiv verification `[VF]` | **RATIFIED 2026-07-21** (text integration pending) |
| AM-11 | §2.3/§14.2 | Make O-3 monitoring concrete: track Shopify's `@idempotent` mutation list, ACP SEP #120, and CrewAI idempotency-backend PR #5822, quarterly. | Vendor docs/issue trackers `[VF]` | **RATIFIED 2026-07-21** |
| AM-12 | §8.1 | BetterBench "46 criteria" vs the camera-ready abstract's "40 practices": keep 46, cite betterbench.stanford.edu + arXiv:2411.12990, note the version drift. | Source comparison `[VF]` | **RATIFIED 2026-07-21** |
| AM-13 | §15 M1 | Two-stage preregistration: Stage-A **design** freeze satisfies M1; Stage-B **execution** freeze happens before M7 runs. | Registered-report staging practice `[EI]` — design live in the DRAFT preregistration §0 | **RATIFIED 2026-07-21** |
| AM-14 | §8.6 | Replace "overlapping CIs" in the falsification criterion with a pre-specified equivalence procedure (TOST with a declared margin). | Statistical-methods review `[EI]` | **RATIFIED 2026-07-21 with validity-review correction:** margins are metric- and tier-specific with a frozen sensitivity table, framed for a named reference adopter profile — no universal margin claim. Corrected text is live in the preregistration §5.3; final margin values are Stage-A freeze parameters (§3 item 11) |
| AM-15 | §5.4 | Clarify the "dashboard" non-goal: §5.4 rejects a hosted multi-tenant SaaS dashboard. A local-first developer workbench UI (no auth layer, no billing, no hosted service) is in scope. | Owner written directive, 2026-07-21 `[DD]` | **RATIFIED 2026-07-21**; implemented as [ADR-0016](decisions/0016-frontend-workbench-stack.md). The independent simplification review's defer-to-post-M8 recommendation was **overruled by the owner** (overrule recorded in ADR-0016) |
| AM-16 | whole document | **Sanitization amendment:** redact personal material from the master doc — §3.1 builder-row personal details, §13 clearance specifics, and related framing in §1.3/§3.2/§3.3/§5.3/§5.4/§14/§15/§16 — replaced with neutral "external clearances" wording. Hash re-pinned: `91cc52fa…ad6c` → `5a452199…1c10`. Pre-redaction wording persists in git history and in accepted ADR-0000 (append-only); see §3 item 13. | Owner written ratification, 2026-07-21 `[DD]` | **RATIFIED and APPLIED 2026-07-21** |
| AM-17 | §6.3/§7.3 | Intent contract carries the dispatchable request model: `adapter_id`, non-identity `parameters` (validated per adapter before persistence), optional `branch_ref`/`event_time`, `schema_version`. Identity derivation unchanged. Fixes validity-review blocker B1 (no public contract carried the destination binding or payload). | Validity review B1; implemented via [ADR-0019](decisions/0019-record-schemas-and-api-contracts.md) + schema change | **Contracts ratified 2026-07-21 (ADR-0019)**; master-doc §7.3 text integration PROPOSED |
| AM-18 | §7.1 | Dimension-B correction: **DUPLICATE keeps its canonical n>1 meaning**; a new **CONTRADICTED** classification covers later authoritative evidence contradicting a settled outcome (false-failure / committed-then-vanished). Rejects the engine draft's DUPLICATE redefinition (validity-review blocker B3). Benchmark duplicate counts come from oracle read-back, never finding counts. | Validity review B3; canonical tables in [rfc-002-engine-design.md](rfc-002-engine-design.md) §3 | **State tables ratified 2026-07-21 (RFC-002)**; master-doc §7.1 text integration PROPOSED |
| AM-19 | §10/§15 | Mark "Apache-2.0" as an assumption subordinate to ADR-0014 (licensing decided at the public-release gate, not M2); update publication mechanics: the working repository is public (owner decision 2026-07-21, final); packaged releases/preprints remain gated by the execution-plan public-release gate. | ADR-0014 Context; owner decision 2026-07-21 | PROPOSED |
| AM-20 | RFC-002 §2.2 (not master doc) | Implementation deviation recorded by T-103: `dispatch_attempts.gate_decision_id` is nullable exactly for attempt kind `c1_replay_probe` (CHECK-coupled: every other kind requires it). Reason: §5.3 item 2 runs the replay probe under the claim discipline but never under the gate (C1 M16), so no gate decision exists for it; the §2.2 sketch's unconditional NOT NULL is unsatisfiable for that kind. | T-103 implementation ([migrations/0002_tables.sql](../migrations/0002_tables.sql)); tested both ways | PROPOSED (RFC-002 §2.2 sketch annotation) |
| AM-21 | ADR-0018 M8 mechanics (not master doc) | Amend ADR-0018's M8 Pages mechanics for the shared Pages slot: one Pages site per repo, so the marketing site (`site/`) serves at `/` and the M8 MkDocs docs move under `/docs/` (RD5 §6.2 recommendation). Required before the first site deploy; the M8 docs plan currently assumes the whole slot. | Site architecture RD5 §6.2 `[EI]`; site package landed at consolidation 2026-07-21 | PROPOSED |
| AM-22 | whole document | **Rename amendment:** targeted product-name find-replace across the master doc — Detent → Irrevon, DetentBench → IrrevonBench (25 token replacements; every other byte preserved). Decision record: [ADR-0023](decisions/0023-rename-to-irrevon.md) (supersedes ADR-011; N1 evidence; counsel-screening caveat preserved). Hash re-pinned (AM-16 mechanics): `5a452199…1c10` → `aef24e81…4812`. Pre-rename wording persists in git history and in append-only records (prior ADRs, this queue's earlier rows, tasks/) by design. | Owner written directive, 2026-07-21 ("the name change has to reflect everywhere") `[DD]` | **RATIFIED and APPLIED 2026-07-21** (owner written directive; applied by the RENAME worker at the owner's direction) |

## 2. Open uncertainties and negative results

Recorded so they are not re-researched or silently assumed away.

- **Twilio test-mode queryability unverified** `[OQ]` — must be spiked before Twilio could
  be chosen as the C2 sandbox (P4).
- **Cordon EuroSys 2027 acceptance: secondary source only** `[OQ]` — do not cite as fact
  until a primary source confirms.
- **No in-the-wild re-synthesis frequency data exists** — negative result, not a search gap;
  DetentBench would generate the first such data.
- **Amadeus orphan sweep infeasible in the self-service tier** — disqualifying for the POC
  C2 adapter despite headline appeal.
- **Cursor .mdc-vs-AGENTS.md precedence unspecified** `[OQ]` — this repo avoids conflicts by
  construction.
- **cli.json argument-pattern deny matching untested** `[OQ]` — the hook layer
  (`.cursor/hooks/deny.sh`) is the tested control.
- **Sandbox ToS position on sustained benchmarking traffic unknown** `[OQ — human]` —
  Shopify dev store and EasyPost test ToS must be reviewed before ADR-0012 closes; a mid-run
  throttle/ban voids benchmark runs (also §3 item 12).
- **Shopify client-credentials token vs `orderCreate` offline-token requirement** `[OQ]` —
  P4 spike item (e) in ADR-0012; the auth model changed January 2026.
- **Destination test-data retention** `[OQ]` — Stripe payments-object retention
  undocumented; Shopify dev-store retention undocumented (low risk); EasyPost test objects
  30 days `[VF]`. Read-backs must not assume indefinite persistence.
- **Seed-level heterogeneity (τ) is unestimable before any run** — Stage-A freeze precedes
  all observation; the preregistration's power table (§5.6) is honest about the resulting
  equivalence-power uncertainty. Structural, not resolvable by more research.
- **Effects multi-effect graph: directive A1 overruled the owner request** `[DD]` — the
  redesign directive requested table and graph modes on Effects; the implementation
  deliberately omits a multi-effect graph because no current contract field supports a
  cross-effect edge (shared adapter/scope/class/timestamp proximity are grouping
  dimensions, not relationships); graph interaction begins only after selecting one
  effect. Compensation (`compensates_finding_id`, RFC-002 §7.3) is the first credible
  future cross-effect edge — reopen when M4 resolve verbs land fixtures carrying it
  (recorded per REDESIGN-BRIEF ruling A1, 2026-07-21).
- **TypeScript 7.x (native compiler) vs latest 5.x/6.x line** `[OQ]` — decide at `web/`
  scaffold by running the full toolchain (ADR-0016). *Decided at scaffold 2026-07-21 per
  that rule:* TS 7.0.2 typechecks but typescript-eslint 8.64 crashes against it; pinned
  TS 5.9.3, the newest stable line the full toolchain passes (recorded in
  [../web/README.md](../web/README.md)). Reopens when typescript-eslint supports 7.x.

## 3. Human action queue

| # | Item | Blocks | Status |
|---|---|---|---|
| 1 | **TOP PRIORITY — development-environment review item DE-1 (details held privately):** complete the environment migration before any implementation work. | All implementation (execution-plan P1 gate) | OPEN |
| 2 | Send the written external-clearance requests (master doc §13; details tracked privately). | All publication | OPEN |
| 3 | Countersign [ADR-0000 scope freeze](decisions/0000-scope-freeze.md) and [ADR-0015](decisions/0015-schema-validation-tooling.md) (both recorded accepted; explicit countersign requested). | — | OPEN |
| 4 | Run the name screen for "Detent" (GitHub/PyPI/npm/company/trademark — PyPI explicitly, per ADR-0018); adopt fallback if it collides. **Collision evidence recorded 2026-07-21 (FR3 identity research, carried into [ADR-0014](decisions/0014-licensing.md)):** PyPI `detent` is **taken** (v1.2.0, AI-agent action-safety space); `digitaldrywood/detent` (GitHub, Go, active AI-agent orchestration); DetentLabs (detentlabs.ai, same safety metaphor). npm/crates.io available. Items 1–2 plausibly meet ADR-0011's reopen trigger ("a Detent collision — fall back to a runner-up"); whether the trigger fires is this item's human decision. The screen should now include a USPTO clearance search (trademark strategy is load-bearing per ADR-0014). **Resolution 2026-07-21:** the owner's written directive ("the name change has to reflect everywhere — the code, the docs, the repo name, everything") adopted **Irrevon** per the N1 screen ([ADR-0023](decisions/0023-rename-to-irrevon.md), supersedes ADR-011; ratified as AM-22). The registry half of the screen is recorded (PyPI/npm/crates/GitHub/domains all appeared available for "Irrevon", 2026-07-21); the **counsel IC 9/42 trademark clearance remains OPEN pre-launch** — N1's findings are research, not legal clearance. PyPI `irrevon` registration is now unblocked **pending clearances** (human publication act). | Any release artifact | **RESOLVED 2026-07-21 by owner directive (ADR-0023); counsel trademark screen remains open pre-launch** |
| 5 | Ratify or reject each amendment in section 1. | — | **DONE 2026-07-21** for AM-1..AM-16 (see §1 statuses); AM-17/AM-18 master-doc text integration and AM-19 remain open |
| 6 | Ratify [ADR-0013](decisions/0013-implementation-language.md) after T-000 produces its recommendation. | First code task | **DONE 2026-07-21** |
| 7 | Close the licensing decision ([ADR-0014](decisions/0014-licensing.md)). | Any release artifact | OPEN |
| 8 | Decide on GitHub Pro (branch protection was the rationale). | — | **MOOT while the repo is public** (rulesets free); reconfirm only if visibility ever changes |
| 9 | Ratify the workbench-scope amendment (AM-15) and the frontend-stack ADR. | Frontend implementation | **DONE 2026-07-21** (AM-15 ratified; ADR-0016 accepted) |
| 10 | Owner decision 2026-07-21: repository made public while planning docs still contained personal material — apply or accept sanitization. | — | **RESOLVED 2026-07-21:** sanitization applied as AM-16; visibility is final per the owner. Residual history question is item 13 |
| 11 | **Stage-A freeze parameters + the freeze act** (preregistration §0.1): trials/cell (60 vs 160 power/throughput trade), equivalence margins + sensitivity table, worst-cell gate threshold; then execute the freeze (signed tag + OpenTimestamps + OSF). The pre-freeze draft is public — freeze promptly or accept the front-running exposure in writing. | P3; all benchmark runs | OPEN |
| 12 | Sandbox ToS review for benchmarking use (Shopify dev store primary, EasyPost fallback). | P4 / ADR-0012 close | OPEN |
| 13 | **History question (owner deferred 2026-07-21):** pre-redaction master-doc content (personal details) and the pre-scrub environment note persist in public git history. Options when revisited: accept exposure as-is, or a human-only history rewrite (prohibited to agents) before M8 release mechanics. | — (revisit before M8) | DEFERRED by owner |
| 14 | Enable public-repo security services (settings, human-only): secret scanning + push protection, CodeQL default setup, rulesets/required checks — follow the ordered owner settings checklist in [ci.md](ci.md) (phase 2 of the ruleset must wait until `ci-required` has reported on a real PR). | — (CI workflows landed 2026-07-21; checklist now actionable) | OPEN |
| 15 | Cloud-agent policy: the relaxation proposal was **declined 2026-07-21**; policy remains foreground-only, gated on DE-1 (security-policy). Revisit only after item 1 closes. | — | RECORDED |
| 16 | M8 distribution mechanics per [ADR-0018](decisions/0018-distribution-model.md): PyPI trusted publisher, Pages + MkDocs enable, Zenodo deposit, immutable releases — all human publication acts at the release gate. | M8 | OPEN (not due before M8) |
| 17 | Ratify or reject the three implementation ADRs proposed by T-101/T-102: [ADR-0020](decisions/0020-identity-procedure.md) (identity procedure, owed by RFC-001 §1), [ADR-0021](decisions/0021-record-schemas-admission.md) (record-schema admission per ADR-0019 item 4), [ADR-0022](decisions/0022-migration-runner.md) (migration runner, the ADR-0013 `[OQ]` slot); and the AM-20 deviation annotation. Implementation proceeded per the RFC-002/ADR-0019 contracts; these record acceptance. | — | OPEN (proposed 2026-07-21) |
| 18 | **Rank the licensing goals** (neutrality-first vs. protection-first) and pick the [ADR-0014](decisions/0014-licensing.md) candidate: primary **B (hybrid: engine AGPL-3.0; harness/schemas/SDK Apache-2.0)** vs. runner-up **A (all-Apache-2.0)** — both with the trademark/conformance, NOTICE, and DCO layers. Choosing B additionally requires ratifying a master-doc amendment (extending AM-19) superseding the §10/§15 Apache-2.0 assumption. Precedes item 7 (closing ADR-0014); decision lands at the public-release gate. | Item 7; any release artifact | OPEN (analysis refreshed 2026-07-21) |
| 19 | Close the two remaining OPEN pre-implementation ADRs when their spikes complete: [ADR-0010](decisions/0010-stripe-api-version.md) (Stripe API version pin — §13 blocker, needs the pinned-version contract test) and [ADR-0012](decisions/0012-c2-sandbox.md) (C2 sandbox selection — needs the P4 spike plus the ToS review in item 12). | P4 / M4 adapters | OPEN |
| 20 | **Write and ratify the marketing-site ADR** proposed by RD5 §7 item 1 (next-free number at writing: 0023): `site/` Astro package as the customer-facing surface, Pages deploy gated; supersedes DIST §4.1 row 12's "no brand site" scope while keeping its $0/no-domain/no-SaaS rulings. Related owner rulings RD5 §7 item 3 still owed: (a) Book-a-Demo naming/presence, (b) public contact address or explicit "GitHub-issues-only", (c) confirm DE-1 posture covers `site/` build work. The site package landed at consolidation 2026-07-21 with deploy fully gated (workflow is dispatch-only; Pages enablement is human-only). | First site deploy | OPEN (proposed 2026-07-21) |
| 21 | **ADR id reshuffle note (rebuild cycle, 2026-07-21):** id 0023 was consumed by the rename ADR ([ADR-0023](decisions/0023-rename-to-irrevon.md)); the N2 serve ADR moves to **0024** and the marketing-site ADR of item 20 moves to **0025** (numbers reserved by this note, per the next-free-id rule). Also records: PyPI **`irrevon`** registration is unblocked **pending clearances** (external clearances §13 + counsel trademark screen, item 4) — registration itself is a human publication act; the `irrevon.dev`/`irrevon.com` domain purchases are owner spend decisions on the launch checklist. | — | RECORDED (appended by the RENAME worker) |
