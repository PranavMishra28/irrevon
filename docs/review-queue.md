# Review queue

Three lists a human must act on. **Nothing here is authoritative.** The master doc
([master-doc.md](master-doc.md)) remains the sole source of product truth until an amendment
below is explicitly ratified; ratification integrates the change into a new master-doc version
and re-pins the hash in `scripts/master-doc.sha256`. Agents append to this file; only humans
resolve items.

## 1. Proposed master-doc amendments (status: all PROPOSED)

Refinements surfaced by pre-scaffold research verification. No fabricated citations were found
in the master doc — every named paper, product, and figure checked out against primary
sources; these are refinements, not corrections of fabrications.

| # | Master doc location | Proposed change | Source/evidence |
|---|---|---|---|
| AM-1 | §4.1 | Narrow "no existing benchmark isolates these": MAS-FIRE (arXiv 2602.19843, semantic/coordination fault injection) and Atomix's eval (fault injection + irreversible-leakage counting on mocks) now exist. Rephrase to "no standalone, preregistered benchmark against real production API contracts with a destination read-back oracle." | Research verification vs arXiv, July 2026 `[VF]` |
| AM-2 | §4.3 Atomix row | Update "in-memory dedup" (v1 limit) to the v2 claim: SQLite-backed single-process crash-safe dedup, unit-tested only, explicitly no distributed exactly-once. Differentiation unchanged. | Atomix v2, arXiv 2602.14849 `[VF]` |
| AM-3 | §4.3 ACRFence row | Add strengthening fact: ACRFence's paper validates the attacks but does not implement the ACRFence mitigation itself — attack PoC only. | arXiv 2603.20625 `[VF]` |
| AM-4 | §2.3 | Caveat the Anthropic figures: 73%/0.8% are model-classified estimates; Anthropic notes over-estimation of human involvement, so 73% is an upper bound. | Anthropic autonomy post `[VF]` |
| AM-5 | §7.5 / ADR-010 | Scope ADR-010: Stripe v2 idempotency applies to the /v2 namespace only; PaymentIntents/Charges are v1 (24h, cached-error replay). Pin v1 semantics for payments-namespace endpoints. | Stripe API docs `[VF]` — carried into [decisions/0010-stripe-api-version.md](decisions/0010-stripe-api-version.md) |
| AM-6 | §7.5 C1 examples | Tag QuickBooks Online C1 as `[EI]` pending contract tests: a public SDK issue shows duplicates despite RequestId via the .NET SDK path. | intuit/QuickBooks-V3-DotNET-SDK#352 `[VF]` |
| AM-7 | §8.3/§8.6 | Add composite baseline **B5+B3+B6** (durable runtime + stable op-IDs + provider status check in recovery) to the preregistered plan as the primary comparison; give B7 LLM-budget parity with R's advisory classifier. | Baseline-ladder gap analysis `[EI]` — already reflected in the DRAFT preregistration |
| AM-8 | §5.2/§13 | Add sandbox-selection spike items: Twilio test creds may not persist queryable messages; Amadeus self-service has no list endpoint + session-scoped IDs. Recommend Shopify dev store primary / EasyPost fallback; note Shopify dev-store 5 orders/min cap for throughput planning. | API-doc verification `[VF/EI]` — carried into [decisions/0012-c2-sandbox.md](decisions/0012-c2-sandbox.md) |
| AM-9 | §7.3 CapabilityDeclaration | Add fields `client_ref_field` and `list_queryable` — they determine whether ORPHANED and LOST are detectable per destination. | Per-destination reconcile-hook survey `[EI]` — present as draft fields in [../schemas/capability-declaration.schema.json](../schemas/capability-declaration.schema.json) |
| AM-10 | §4.2 | Credit the effect-class taxonomy {IDEMPOTENT, REVERSIBLE, COMPENSABLE, IRREVERSIBLE} to Revisable-by-Design (arXiv 2604.23283) and Gray 1978 (via Atomix) — independent convergence, preempts a reviewer objection. | arXiv verification `[VF]` |
| AM-11 | §2.3/§14.2 | Make O-3 monitoring concrete: track Shopify's `@idempotent` mutation list (orderCreate absent as of Feb 2, 2026), ACP SEP #120, and CrewAI idempotency-backend PR #5822, quarterly. | Vendor docs/issue trackers `[VF]` |
| AM-12 | §8.1 | BetterBench "46 criteria" vs the camera-ready abstract's "40 practices": keep 46, cite betterbench.stanford.edu + arXiv:2411.12990, note the version drift. | Source comparison `[VF]` |
| AM-13 | §15 M1 | Two-stage preregistration: M1's "preregistered and hash-stamped" is satisfied by a Stage-A **design** freeze (hypotheses, matrix, metrics, analysis rules — no sandbox names); Stage-B **execution** freeze (adapters, artifact hashes, sealed holdout hash) happens before M7 runs. Resolves the sequencing tension that full freeze depends on M4/M5-adjacent work. | Registered-report staging practice `[EI]` — design already in the DRAFT preregistration §0 |
| AM-14 | §8.6 | Replace "overlapping CIs" as the indistinguishability test in the falsification criterion with a pre-specified equivalence procedure (TOST with a declared margin). CI overlap is a statistically weak sameness test. | Statistical-methods review `[EI]` — flagged in the DRAFT preregistration §5 |

## 2. Open uncertainties and negative results

Recorded so they are not re-researched or silently assumed away.

- **Twilio test-mode queryability unverified** `[OQ]` — test credentials likely return canned
  responses without persisting queryable message records; must be spiked before Twilio could
  be chosen as the C2 sandbox (P4).
- **Cordon EuroSys 2027 acceptance: secondary source only** `[OQ]` — do not cite the
  acceptance as fact until a primary source confirms.
- **No in-the-wild re-synthesis frequency data exists** — searches found no field rates for
  re-synthesized duplicate effects anywhere; DetentBench would generate the first. Negative
  result, not a gap in the search.
- **Amadeus orphan sweep infeasible in the self-service tier** — no list endpoint and
  session-scoped test order IDs make the sweep impossible there; disqualifying for the POC C2
  adapter despite headline appeal.
- **Cursor .mdc-vs-AGENTS.md precedence unspecified** `[OQ]` — official docs do not define
  conflict order; this repo avoids conflicts by construction (rules deepen, never contradict).
- **cli.json argument-pattern deny matching untested** `[OQ]` — multi-word `command:args`
  patterns (e.g. `Shell(git:push --force*)`) are documented only via a single-token example;
  the hook layer (`.cursor/hooks/deny.sh`) is the tested control, and it has a passing
  deny/allow test matrix.

## 3. Human action queue

| # | Item | Blocks |
|---|---|---|
| 1 | **TOP PRIORITY — environment red flag:** the development machine is employer-MDM-managed and the IDE is signed into an employer team account. Move development to a personal machine and personal account before any implementation work. | All implementation (execution-plan P1 gate) |
| 2 | Send written requests: employer IP clearance + immigration guidance (master doc §13). | All publication |
| 3 | Countersign [ADR-0000 scope freeze](decisions/0000-scope-freeze.md) (recorded as accepted on master-doc authority; explicit countersign requested). | — |
| 4 | Run the name screen for "Detent" (GitHub/PyPI/npm/company/trademark); adopt fallback if it collides. | First public commit |
| 5 | Ratify or reject each amendment in section 1; ratified ones get integrated into a new master-doc version with a re-pinned hash. | P3 (for §8-touching amendments AM-7/AM-13/AM-14) |
| 6 | Ratify [ADR-0013](decisions/0013-implementation-language.md) after T-000 produces its recommendation. | First code task |
| 7 | Close the licensing decision ([ADR-0014](decisions/0014-licensing.md)). | Any public step |
| 8 | Decide on GitHub Pro (enforced branch protection on the private repo — the one paid feature with real security payoff for agent-driven development) when code lands. | — (M2) |
