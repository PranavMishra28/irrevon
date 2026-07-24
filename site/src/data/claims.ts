// The claims registry: every key claim on the site lives here —
// claim text, source (doc + section), epistemic label, badge. Pages reference
// claims by id via <Source id="…"/>; scripts/build-claims-md.mjs renders the
// committed site/CLAIMS.md table from this file so "cite sources per claim"
// stays mechanical and reviewable in one diff.
//
// Epistemic labels per master doc §0: VF verified fact (cited) · EI
// evidence-backed inference · TH testable hypothesis · DD design decision ·
// OQ unresolved open question.

export type BadgeKind = "recorded" | "conceptual" | "preregistered";
export type EpistemicLabel = "VF" | "EI" | "TH" | "DD" | "OQ";

export interface ClaimEntry {
  claim: string;
  source: string;
  label: EpistemicLabel;
  badge?: BadgeKind;
}

export const claims = {
  // ── Problem and evidence ────────────────────────────────────────────────
  "problem-ambiguous-outcome": {
    claim:
      "When an agent crashes mid-call, retries a timeout, or re-synthesizes arguments, it can charge twice, book twice, or leave an orphaned effect no process reconciles.",
    source: "master doc §2.1",
    label: "EI",
  },
  "resynthesis-defeats-keys": {
    claim:
      "Semantic re-synthesis defeats idempotency keys: under temperature 0, floating-point nondeterminism yields different token sequences on retry, so the re-synthesized call carries a different reference ID and the destination treats it as new. A 12-framework survey found none enforce exactly-once at the tool boundary.",
    source: "master doc §2.2 (ACRFence, arXiv 2603.20625)",
    label: "VF",
  },
  "framework-duplicate-issues": {
    claim:
      "Open issues in LangGraph and CrewAI document tool re-execution on retry firing duplicate payments and emails; two independent parties confirmed the same failure mode.",
    source: "master doc §2.2",
    label: "VF",
  },
  "anthropic-low-frequency": {
    claim:
      "Irreversible actions are rare as a share of traffic: ~0.8% of 998,481 sampled tool calls (Anthropic, Feb 2026). Model-classified estimates; the human-involvement figure is an upper bound (AM-4 caveat). The problem is high-severity, low-frequency.",
    source: "master doc §2.3 + review queue AM-4",
    label: "VF",
  },

  // ── Recorded artifact (the flagship demo) ───────────────────────────────
  "demo-provenance": {
    claim:
      "The demo transcript is recorded from a real engine run — seed 777, engine commit 0a22114 — against the reference C2 destination (queryable status, no honored idempotency). Reproducible from the repository.",
    source: "web/fixtures/canonical/provenance.json",
    label: "VF",
    badge: "recorded",
  },
  "demo-sequence": {
    claim:
      "Recorded sequence: intent persisted (PERSISTED) → dispatch response lost (AMBIGUOUS) → process SIGKILLed (exit status −9) → restart scans 1 record, adjudicates 1 → destination query confirms the effect exists → SETTLED_COMMITTED + CONFIRMED_UNIQUE → a re-synthesized retry (different parameters, digest recorded) collapses to the same identity and is denied by the dedup check (decision 2).",
    source: "web/fixtures/canonical/demo-artifact.json (events)",
    label: "VF",
    badge: "recorded",
  },
  "demo-contrast": {
    claim:
      "Recorded contrast: the Irrevon leg ends with 1 destination effect and the duplicate rejected; the B5 baseline leg (durable runtime, stable op-IDs, idempotency keys sent) under the identical fault schedule retries on restart and ends with 2 destination effects — the C2 destination ignores the key.",
    source: "web/fixtures/canonical/demo-artifact.json (summary)",
    label: "VF",
    badge: "recorded",
  },
  "workbench-fixture-screens": {
    claim:
      "The workbench pictured is the real read-only evidence viewer running against schema-validated fixtures captured from a real engine run (seed 777); the SYNTHETIC FIXTURE banner is part of the product.",
    source: "web/README.md + web/fixtures/canonical/provenance.json",
    label: "VF",
    badge: "recorded",
  },

  // ── Mechanism ───────────────────────────────────────────────────────────
  "identity-stable-ids": {
    claim:
      "Effect identity derives from stable upstream business identifiers, never model output: intent_id = hash(canonical stable ids + effect_type + scope); idempotency evidence derives only from operation_id. Conformance-tested: no key-derivation path reads model output.",
    source: "master doc §7.2, §12.1 + RFC-002 §1",
    label: "DD",
  },
  "persist-before-dispatch": {
    claim:
      "No dispatch without a durable PERSISTED record carrying operation_id and idempotency evidence — crash-before-persist is therefore provably effect-free.",
    source: "master doc §7.4",
    label: "DD",
  },
  "reconcile-by-query": {
    claim:
      "Ambiguous outcomes are resolved by querying the destination's authoritative status — asking the destination, not believing the caller. Unknown destination errors map to AMBIGUOUS, never FAILED, so evidence is never discarded.",
    source: "master doc §6.1, §7.5, §9",
    label: "DD",
  },
  "state-model": {
    claim:
      "State is three orthogonal dimensions: A execution lifecycle (INTENDED → PERSISTED → DISPATCHED → SETTLED/AMBIGUOUS/CANCELLED), B reconciliation classification (UNRECONCILED · CONFIRMED_UNIQUE · DUPLICATE · LOST · CONTRADICTED · ORPHANED), C resolution status (OPEN → … → CLOSED). Orphans are representable only as findings — a ledger-keyed state machine cannot express them.",
    source: "master doc §7.1 + RFC-002 §3 (canonical tables)",
    label: "DD",
  },
  "recovery-adjudicate": {
    claim:
      "On restart the ledger is replayed and every DISPATCHED/AMBIGUOUS record is adjudicated before any new dispatch of the same operation. Re-dispatch requires confirmed absence (C2) or in-window replay (C1) plus fresh authority. Never re-dispatch on belief.",
    source: "master doc §7.4 + RFC-002 §0/§7",
    label: "DD",
  },
  "tiers-table": {
    claim:
      "Guarantees are destination-tiered: C1 (idempotency-keyed) duplicates are PREVENTED natively — Irrevon adds no advantage there, the expected null; C2 (queryable) duplicates are DETECTED via query with safe re-dispatch after confirmed absence; C3 (opaque) lost and orphaned effects are UNDETECTABLE — an impossibility boundary demonstrated openly.",
    source: "master doc §7.5",
    label: "DD",
  },
  "no-exactly-once": {
    claim:
      "No universal exactly-once exists (Two Generals / FLP). The achievable target is at-least-once delivery plus idempotent or reconciled processing.",
    source: "master doc §5.4, §7.5",
    label: "VF",
  },
  "compensation-not-rollback": {
    claim:
      "True rollback of an externalized irreversible effect is impossible. Compensation is a new effect with its own failure modes — measured, never assumed.",
    source: "master doc §5.4, §7.5 + ADR-007 (§11)",
    label: "DD",
  },
  "capability-declaration": {
    claim:
      "Every adapter ships a version-pinned, cited, machine-readable capability declaration (tier, idempotency semantics, queryability, consistency bounds) — adapters must prove their destination's semantics in writing. Contract drift forces a declaration update, retest, and a deviation ADR.",
    source: "master doc §7.6 + ADR-005 (§11) + schemas/capability-declaration.schema.json",
    label: "DD",
  },

  // ── Engine status ───────────────────────────────────────────────────────
  "components-responsibilities": {
    claim:
      "Components: Intent Registrar → Effect Ledger → Commit Gate → Dispatcher → Reconciliation Engine (+ Orphan Sweep), with capability-tiered adapters and an advisory-only Outcome Classifier.",
    source: "master doc §6.1",
    label: "DD",
  },
  "classifier-advisory": {
    claim:
      "The Outcome Classifier is advisory-only and architecturally unable to reach the gate or resolve APIs — model output carries no authority. Tested (M3 conformance row).",
    source: "master doc §6.1, §6.3, §12.1 + ADR-006 (§11)",
    label: "DD",
  },
  "implemented-first-slice": {
    claim:
      "Implemented today: identity, append-oriented ledger with locked transition functions, commit gate, dispatcher, reconciliation, crash recovery, orphan sweep, continuous worker, reference destinations, read-only Workbench, benchmark development harness, and local package build. Stripe/EasyPost are never-live-called drafts; no package or result has been published.",
    source: "docs/project-status.json + README.md + RFC-002 + migrations/",
    label: "VF",
  },
  "single-writer-scope": {
    claim:
      "The ledger is single-writer in the POC — a documented scaling limit, with per-scope serialization of in-flight dispatch.",
    source: "master doc §7.4 + ADR-002 (§11)",
    label: "DD",
  },

  // ── Benchmark ───────────────────────────────────────────────────────────
  "prereg-draft-status": {
    claim:
      "The IrrevonBench preregistration is a DRAFT — nothing is frozen and no section carries integrity weight. Synthetic S-REF engineering pilots have occurred and are disclosed; no live-sandbox observation or confirmatory run has occurred. Stage A must precede live-sandbox work and Stage B must precede confirmatory execution; freezing is a human act.",
    source: "docs/benchmark-preregistration.md §0–§0.2",
    label: "VF",
    badge: "preregistered",
  },
  "no-results-exist": {
    claim:
      "No scientific or confirmatory benchmark result exists. Developmental refdest smoke pilots—including ADR-0032's 488-effect attribution-hardening pilot—are engineering evidence only and cannot support efficacy, live-provider, hypothesis, or publish-threshold claims.",
    source: "docs/benchmark-preregistration.md §0.2 + ADR-0032",
    label: "VF",
    badge: "preregistered",
  },
  "developmental-pilot-disclosure": {
    claim:
      "Pre-freeze harness and CLI smoke pilots exercised public dev fixtures and injected faults against the synthetic reference destination. The full inventory is disclosed; outputs are permanently non-confirmatory S-REF mechanism evidence and the eventual Stage-A registration may not be called pristine or pre-observation.",
    source: "docs/benchmark-preregistration.md §0.2 + docs/benchmark.md status",
    label: "VF",
    badge: "preregistered",
  },
  "benchmark-crisis": {
    claim:
      "Benchmark credibility failed publicly in 2026: OpenAI stopped reporting SWE-bench Verified (Feb 23, 2026) after an audit found gains increasingly reflect training-time exposure, and retracted its SWE-bench Pro recommendation (July 8, 2026) after flagging ~27–34% of public tasks as broken.",
    source: "master doc §8.1",
    label: "VF",
  },
  "credibility-controls": {
    claim:
      "IrrevonBench self-scores against BetterBench (46 lifecycle criteria), ships Datasheets for Datasets documentation and Croissant metadata, freezes hypotheses/metrics/analysis before live-sandbox and confirmatory evidence, and seals a private held-out fault-seed split that never enters the repository. Disclosed S-REF development pilots are excluded from scientific claims.",
    source: "master doc §8.1 + preregistration §0, §0.2, §7 (AM-25 proposed)",
    label: "DD",
    badge: "preregistered",
  },
  "baseline-ladder": {
    claim:
      "The draft preregistration pre-specifies the baseline ladder B0–B7 plus R and forbids weakening it so the proposed system wins; the preselected primary comparator is the composite B5+B3+B6, with B5 reported alongside — superiority must reject against both.",
    source: "master doc §8.3 + preregistration §1 (AM-7 as ratified)",
    label: "DD",
    badge: "preregistered",
  },
  "kill-criterion": {
    claim:
      "The falsification criterion is pre-committed: if the composite comparator is statistically equivalent to or better than Irrevon on every primary metric of the confirmatory stratum (TOST, with a worst-cell gate), Irrevon is unnecessary and the project is reframed as a teaching artifact. The benchmark is explicitly not designed so the system must win.",
    source: "preregistration §1 (implements master doc §8.6 + AM-14)",
    label: "TH",
    badge: "preregistered",
  },
  "c1-null-precommit": {
    claim:
      "The pre-committed C1 null: on C1 destinations Irrevon is expected to show NO advantage over native idempotency on duplicate rate, and that null will be reported as prominently as any positive result.",
    source: "master doc §1.2, §8.6 + preregistration §1 (H0-C1)",
    label: "TH",
    badge: "preregistered",
  },
  "metrics-definitions": {
    claim:
      "Metrics use oracle-fixed, arm-independent denominators: duplicate-effect rate, orphaned-effect rate, lost-legitimate-effect rate, false-suppression rate, unresolved-ambiguous rate, precision/recall vs oracle, human-review rate, time-to-detect, compensation correctness.",
    source: "master doc §8.4 + preregistration §4",
    label: "DD",
    badge: "preregistered",
  },
  "stats-discipline": {
    claim:
      "≥5 seeds per cell (10 planned); means with confidence intervals and effect sizes, never point estimates; every executed cell reported; INVALID runs retained and marked, never deleted; second-machine reproduction and independent recomputation of a random 10% of cells before any public claim.",
    source: "master doc §8.5 + preregistration §5, §6",
    label: "DD",
    badge: "preregistered",
  },
  "oracle-design": {
    claim:
      "Fixtures are the oracle: seeded workloads with known true intent identity; re-synthesis variants pre-generated, human-spot-checked, frozen; faults injected client-side against real destinations — the benchmark tests the client/contract boundary and says so.",
    source: "master doc §8.2 + preregistration §3",
    label: "DD",
    badge: "preregistered",
  },
  "stamping-planned": {
    claim:
      "Freeze stamping (planned, not yet executed): canonical tree hash → signed git tag → OpenTimestamps stamp → OSF registration of the same document and hash. Two-stage: design freeze before any sandbox observation; execution freeze before any confirmatory run.",
    source: "preregistration §0",
    label: "DD",
    badge: "preregistered",
  },
  "venue-plan": {
    claim:
      "Publication path (a plan, not an achievement): arXiv preprint → agents/reliability workshop → NeurIPS Datasets & Benchmarks track. No preprint exists today.",
    source: "master doc §8.7 + preregistration §9",
    label: "DD",
  },

  // ── Research / prior art ────────────────────────────────────────────────
  "prior-art-credited": {
    claim:
      "Not novel, and credited: the outbox pattern, idempotency keys (Stripe, Kafka EOS), sagas/compensation, durable execution (Temporal, DBOS, Restate, Inngest), staged commit for agents (Cordon, Atomix), record-and-replay (ACRFence), financial reconciliation (Formance, Modern Treasury).",
    source: "master doc §4.2",
    label: "VF",
  },
  "novelty-boundary": {
    claim:
      "As of the documented July 2026 survey, we did not identify a standalone preregistered benchmark jointly evaluating irreversible agent effects across destination capability tiers with destination read-back and a precommitted duplicate/orphan/lost/contradicted/false-suppression analysis. Irrevon is a pre-freeze attempt to build it; no priority, patentability, or scientific-result claim is made.",
    source: "site research/prior-art survey + master doc §4.1 + review queue AM-1",
    label: "EI",
  },
  "epistemic-labels": {
    claim:
      "Every project document labels its claims: [VF] verified fact (cited), [EI] evidence-backed inference, [TH] testable hypothesis, [DD] design decision, [OQ] open question. An unlabeled claim reads as a design decision.",
    source: "master doc §0",
    label: "VF",
  },

  // ── Security & trust ────────────────────────────────────────────────────
  "trust-boundary": {
    claim:
      "Model-generated content reaches the deterministic core only through the validated intent contract; advisory classifier output cannot reach gate or resolve APIs (architecturally enforced and tested).",
    source: "master doc §6.3, §9, §12.1",
    label: "DD",
  },
  "ledger-privacy": {
    claim:
      "The ledger stores metadata and digests, not raw payloads where avoidable; a redaction pipeline governs exported evidence bundles; no end-customer personal data or partner production data in any record.",
    source: "master doc §9 + RFC-002 §0 principle 5",
    label: "DD",
  },
  "zero-telemetry": {
    claim:
      "Zero telemetry, zero analytics, zero external requests — engine and workbench. The workbench's no-external-request and read-only properties are E2E-enforced. This site is static, self-hosts its fonts, and makes no third-party requests; its only measurement is Vercel's cookieless, same-origin Web Analytics and Speed Insights (owner-enabled, ADR-0029) — an allowance the site's budget tests pin to exactly those two first-party scripts.",
    source: "web/README.md (enforced budgets and tests) + site/e2e/budget.spec.ts + docs/decisions/0029-site-vercel-analytics.md",
    label: "VF",
  },
  "supply-chain": {
    claim:
      "Supply-chain posture as practiced: pnpm with lifecycle scripts blocked, a 7-day publish-to-installable delay, provenance no-downgrade, exotic-subdep blocking, exact pins and frozen lockfiles; CI actions SHA-pinned; secret scanning on every commit. Verifiable in the repository source.",
    source: "web/pnpm-workspace.yaml + docs/ci.md + Makefile",
    label: "VF",
  },
  "security-non-claims": {
    claim:
      "What Irrevon is NOT: not an authorization or approval gateway, not an audit-compliance product, no SOC 2 or ISO certification (none exists), not a hosted service — and the LLM never holds sole authority over an irreversible action.",
    source: "master doc §5.4, §9",
    label: "DD",
  },
  "incident-taxonomy": {
    claim:
      "An incident taxonomy and response procedure exist and are public: declare → classify (Sev-1..3) → contain via the deny-list → preserve evidence first → RCA with deadlines → close only with a corrective change and a seeded regression test.",
    source: "master doc §12.4",
    label: "DD",
  },
  "credentials-policy": {
    claim:
      "Credentials are sandbox-only in a secret store; pre-commit secret scanning; a production-scope credential anywhere is an immediate stop-and-rotate incident.",
    source: "master doc §9",
    label: "DD",
  },

  // ── Status, licensing, availability ─────────────────────────────────────
  "install-gated": {
    claim:
      "Planned distribution (uvx / uv tool install / pipx / pip, one PyPI package with the embedded workbench) is decided but gated: publication requires the public-release gate — clearances granted in writing, the counsel trademark screen, and the licensing decision. Every install command for it renders as PLANNED, never as available today.",
    source: "docs/decisions/0018-distribution-model.md + docs/review-queue.md §3 item 4 + execution plan (public-release gate)",
    label: "VF",
  },
  "no-releases": {
    claim:
      "No release exists: zero git tags, no package, no release artifact. The changelog is computed from git tags at build time, so its empty state is derived, not asserted — the first entry appears when the first signed tag exists, which is human-gated.",
    source: "repository state (git tag --list) + execution plan (public-release gate)",
    label: "VF",
  },
  "roadmap-no-dates": {
    claim:
      "The roadmap is phases and gates, never dates: order is load-bearing (the Stage-A preregistration freeze precedes every live-sandbox observation, while disclosed synthetic S-REF development pilots remain non-confirmatory), and nothing in the execution plan is a schedule or a commitment.",
    source: "docs/execution-plan.md (ordering rationale + gate notes)",
    label: "VF",
  },
  "docs-rendered-provenance": {
    claim:
      "Rendered repository documents on this site are mechanical, drift-gated copies: each carries its source path and content sha256, a sync script regenerates them, and CI fails on any byte drift — the repository copy is always canonical.",
    source: "site/scripts/sync-docs.mjs + site/docs-manifest.json (checked in CI via make site-check)",
    label: "VF",
  },
  "quickstart-real": {
    claim:
      "The working quickstart is clone + uv + Docker: uv sync --locked, irrevon init, docker compose up, irrevon doctor, irrevon demo. There is no package-index install — nothing is published.",
    source: "README.md (Quickstart)",
    label: "VF",
  },
  "not-published": {
    claim:
      "Pre-release: not on any package index. The name is decided — Irrevon (ADR-0023, superseding ADR-011); the PyPI name 'irrevon' appeared available at screening and its registration is unblocked pending external clearances and the counsel trademark screen. When published, the install will be `uv tool install irrevon` — future tense until then.",
    source: "docs/decisions/0023-rename-to-irrevon.md + docs/review-queue.md §3 item 4",
    label: "VF",
  },
  "license-apache2": {
    claim:
      "Licensed under Apache-2.0 (owner ratification 2026-07-21; ADR-0028 resolves ADR-0014's license half; LICENSE + NOTICE at the repository root). Outside contributions are open under inbound=outbound Apache-2.0 with mandatory DCO 1.1 sign-off and no CLA (ADR-0035).",
    source:
      "LICENSE + LICENSING.md + CONTRIBUTING.md + docs/decisions/0028-apache-2-license.md + docs/decisions/0035-external-contributions.md",
    label: "VF",
  },
  "thirty-min-target": {
    claim:
      "Integration target, stated as a target with a test: a stranger integrates against one sandbox in under 30 minutes (the stranger test). Not yet an achievement.",
    source: "master doc §10, §12",
    label: "TH",
  },
  "non-goals": {
    claim:
      "Binding non-goals: not a durable-execution runtime, auth layer, approval gateway, dashboard, or hosted SaaS; no billing; not a payments/clearing protocol; no revenue-bearing activity pending external clearances.",
    source: "master doc §5.4",
    label: "DD",
  },
  "solo-governed": {
    claim:
      "Solo-maintained open research project, built under a documented agent-execution policy; the master document is hash-pinned, decision records are append-only, and unresolved questions live in a human-only review queue — decisions are written down and never silently rewritten.",
    source: "docs/security-policy.md + AGENTS.md + docs/review-queue.md",
    label: "VF",
  },
} as const satisfies Record<string, ClaimEntry>;

export type ClaimId = keyof typeof claims;
