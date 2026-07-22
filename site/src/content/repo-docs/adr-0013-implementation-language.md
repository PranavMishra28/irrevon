---
title: "Choose the implementation language and core stack"
sourcePath: "docs/decisions/0013-implementation-language.md"
sourceSha256: "f1672d5ce9e55e753bc91beaf913e5d3206f777d44847c028724d306551ad07c"
syncedAt: "2026-07-22"
section: "Decisions"
renderTitle: true
adr:
  id: "ADR-0013"
  status: "accepted (ratified in writing by the owner, 2026-07-21)"
  date: "2026-07-20"
  supersedes: "—"
---

## Context

Deliberately deferred so the absence of a decision is not mistaken for an accident. No code
may be written before this closes. Evidence gathered pre-scaffold:

- **Ecosystem gravity is Python-first** `[EI]`: the integration surface (LangGraph, CrewAI),
  the OSS twins (agent-ledger, SafeAgent), the closest academic system (Atomix), and the
  nearest funded entrant's SDK (Bylaw) are all Python. Python maximizes integration
  credibility and contributor pool for the project's primary audience (§3.1, §14.1).
- **Property testing is a hard requirement** (§12.2: ≥1,000 cases/invariant): candidate
  ecosystems must have a mature framework (Hypothesis / proptest / fast-check / jqwik-class).
- **Storage:** Postgres is an inherited constraint (ADR-002/§6.1 — single-writer append-only
  ledger, row locking), not reopened here; every candidate has a mature driver, so it cannot
  disqualify any option. A **SQLite-quickstart / Postgres-benchmark** split is an option worth
  weighing for the <30-minute stranger test (Atomix ships SQLite; precedent exists) `[EI]`.
- **Coding-agent fluency** (training-data density) and solo maintainability at ~10 hrs/week
  weigh heavily for a solo builder.
- The deterministic core is pure logic + I/O at the edges; no performance argument for a
  systems language has been made.

## Decision

**Accepted — ratified in writing by the owner on 2026-07-21** (human queue item 6), adopting
the T-000 proposal appended below: implement the POC core, benchmark harness, and first
adapters in **Python (CPython 3.13.x)**, with `uv` for packaging/lockfile and the stranger
quickstart; **pytest + Hypothesis** (`@given` + stateful `RuleBasedStateMachine`) satisfying
§12.2's ≥1,000 cases/invariant; **psycopg 3** (sync — single-writer POC per ADR-002);
ledger schema as plain-SQL, language-neutral migrations (runner chosen at M2 bootstrap
`[OQ]`); **`rfc8785`** as the RFC 8785/JCS encoder, version-pinned, guarded by
cross-implementation conformance vectors in CI, and vendor-ready; stdlib `hashlib.sha256`;
and a strict type-checking gate in CI (checker chosen at M2 `[OQ]`). One deviation from the
proposal, per the same 2026-07-21 reconciliation: OpenTelemetry SDK adoption is **deferred**
— v0.1 ships JSONL structured logging plus ledger-backed inspection only (see
docs/rfc-002-engine-design.md; observability instrumentation was cut from the first slice).
A second-language SDK stays possible by construction (frozen schemas + SQL) and is deferred
until demand exists.

## Alternatives

One-line reasons recorded in the ratified proposal below: TypeScript/Node (no winning
criterion; npm supply-chain posture), Go (cross-language integration cost; property-testing
and telemetry gaps), Rust (slowest solo iteration; no performance case), hybrid
(premature second surface).

## Consequences

Closes the toolchain for M2 bootstrap (test runner, property-test framework, Postgres driver,
migration tooling); unlocks the RFC-001 identity ADR (JCS encoder availability check per
candidate).

## Risks

Choosing for ecosystem gravity over type-safety may cost refactoring ease later; the
language-neutral RFC/schemas bound that risk (a rewrite re-implements against frozen
contracts).

## Reopen trigger

The primary integration ecosystem (agent frameworks, §11 ADR-009 audience) shifts materially
away from the chosen language; or a load-bearing stack component (Hypothesis, psycopg,
`rfc8785`) becomes unmaintained without a viable pin/vendor path.

---

## T-000 proposal — **RATIFIED 2026-07-21** (adopted into the Decision above)

*Appended 2026-07-20 by [T-000](../../tasks/T-000-language-stack-spike.md); ratified in
writing by the owner on 2026-07-21 and adopted into the Decision section above. The full
comparison with the scored criteria matrix and spike transcripts lived in local-only scratch
material (consumed and discarded at integration). Verification is against primary sources
current as of July 2026; disposable spikes in gitignored `.scratch/spikes/` were
owner-authorized in writing (superseding this task's "no toolchains" review trigger); no
product code was written.*

### Proposed Decision text

Implement the POC core, benchmark harness, and first adapters in **Python (CPython 3.13.x)**,
with: `uv` for packaging/lockfile and the stranger quickstart; **pytest + Hypothesis**
(`@given` + stateful `RuleBasedStateMachine`) as the test stack satisfying §12.2's ≥1,000
cases/invariant; **psycopg 3** (sync — the POC is single-writer per ADR-002) as the Postgres
driver; ledger schema expressed as **plain-SQL migrations** kept language-neutral (runner tool
chosen at M2 bootstrap `[OQ]`); **`rfc8785`** (Trail of Bits) as the RFC 8785/JCS encoder,
version-pinned and guarded by cross-implementation conformance vectors in CI; stdlib
`hashlib.sha256` for hashing; **OpenTelemetry Python SDK** (traces/metrics Stable) for
telemetry; and a strict type-checking gate in CI (checker choice at M2 bootstrap `[OQ]`).
A second-language SDK stays possible by construction (frozen schemas + SQL) and is deferred
until demand exists.

### Evidence highlights

- **Spike (verified `[VF]`):** four independent JCS implementations — Python `rfc8785` 0.1.4,
  Node `canonicalize` 3.0.0, Go `gowebpki/jcs` v1.0.1, Rust `serde_jcs` 0.1.0 — produced
  **byte-identical canonical output** (equal SHA-256) on all four shared vectors, including an
  RFC 8785 appendix-style number/string torture vector and a scrambled-key-order vector. The
  RFC-001 §1 identity procedure is therefore implementable in every candidate, and
  cross-language conformance vectors are cheap to keep in CI.
- **Spike (verified `[VF]`):** Hypothesis 6.157.2 sustained 2,068 property cases plus 1,000
  stateful (`RuleBasedStateMachine`) examples / 20,628 rule invocations on a toy ledger
  lifecycle machine in ~5.4 s — comfortably above the §12.2 floor. fast-check 4.9.0 (2,000 +
  1,000 model runs), rapid 1.3.0 (1,000 + 1,000), and proptest 1.11.0 (2,000) also pass.
- **Currency check `[VF]` (July 2026):** Hypothesis releases weekly (6.157.0 on 2026-07-19,
  <https://pypi.org/project/hypothesis/>); psycopg 3.3.4 (2026-05-01,
  <https://pypi.org/project/psycopg/>); OTel status — Python/JS traces+metrics Stable with
  logs in Development, Go logs Beta, Rust all-Beta
  (<https://opentelemetry.io/docs/languages/>).
- **Ecosystem gravity `[EI]`:** unchanged from the Context section above — the integration
  surface, OSS twins, closest academic system, and nearest entrant SDK remain Python-first.

### Alternatives (one-line reason each lost)

- **TypeScript/Node** — beats Python on no criterion, and npm's ongoing worm-class
  supply-chain campaign (Shai-Hulud, ≥500 packages, CISA alert 2025-09-23, four variants
  through mid-2026 `[VF]`
  <https://www.cisa.gov/news-events/alerts/2025/09/23/widespread-supply-chain-compromise-impacting-npm-ecosystem>)
  is the worst dependency-trust posture for a product whose subject is trust boundaries.
- **Go** — best packaging (static binary) and an excellent, actively hardened driver (pgx
  5.10.0 `[VF]`), but the Python-first integration surface would make every adapter and
  harness integration cross-language, and its one live property framework (rapid; gopter
  dormant since 2020 `[VF]`) plus Beta OTel logs make it strictly costlier for this scope.
- **Rust** — strongest type system, but slowest solo iteration at ~10 hrs/week, OTel Beta
  across all three signals `[VF]`, and the I/O-bound core gives the systems language nothing
  to pay for.
- **Hybrid (Python core + second SDK now)** — premature: contracts/schemas/SQL are already
  language-neutral and spike-verified byte-compatible, so a later SDK is cheap; two surfaces
  now double maintenance for zero users `[EI]`.

### Negative findings (recorded against the leaning, per T-000)

1. `rfc8785` is a near-dormant micro-library `[VF]`: last release 2024-09-27; the RFC's own
   Appendix G references the JS implementation, not a Python one. Mitigation: pin, CI
   conformance vectors (from the spike), vendor-ready (Apache-2.0). Not disqualifying — the
   spec is frozen and the library passed every cross-implementation vector.
2. Hypothesis is 20–200× slower per case than fast-check/rapid/proptest on the same property
   `[VF]` (spike timings) — seconds per invariant at the §12.2 floor, fine for M3; budget CI
   minutes for the M6 fault-matrix grid.
3. Python is the weakest static-safety candidate `[EI]` — mitigated by the strict-typing
   gate, the §12.1 exhaustive state-matrix tests, and the bounded-rewrite risk already
   recorded in Risks above.

None of these meet T-000's "Context section itself seems wrong" escalation trigger.
