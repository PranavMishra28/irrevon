---
id: ADR-0023
title: Rename the project — Detent → Irrevon (engine), DetentBench → IrrevonBench (benchmark)
status: accepted (owner written directive, 2026-07-21)
date: 2026-07-21
supersedes: ADR-011 (working name "Detent", master doc §11)
---

## Context

ADR-011 adopted "Detent" as a **working** name with a pre-committed reopen trigger:
"Registry/trademark screen reveals a Detent collision — fall back to a runner-up." The
screen ran on 2026-07-21 (review-queue §3 item 4 evidence, then the independent N1 naming
exploration) and the trigger fired on three independent collisions, all in the project's own
field `[VF]`:

1. **PyPI `detent` is taken by a same-audience product** (v1.2.0, active, Apache-2.0): a
   "verification runtime that intercepts AI coding agent file writes … and rolls back
   atomically," with the CLI surface `detent init / run / status / rollback`
   ([pypi.org/project/detent](https://pypi.org/project/detent/)). Severity: **HIGH — this is
   the decisive collision.** It is not a squat; the audience (developers wiring safety layers
   around AI agents) is identical, and its pitch ("intercept, verify, rollback") is genuinely
   confusable with "persist, dispatch, reconcile." `pip install detent` would forever install
   a competitor; a renamed package (`detent-engine`) breaks the name-extension requirement on
   day one. PyPI names are permanent — this collision could never be fixed after publication.
2. **`digitaldrywood/detent`** — an active Go project (v0.37.0): AI coding-agent orchestration
   with a `detent` CLI (`detent doctor` …) and web dashboard.
3. **DetentLabs** (detentlabs.ai) — the same clicks-into-place safety metaphor, web3.

With at least two active prior users in AI/agent software, any "Detent" mark in IC 9/42 would
enter the field as the **junior** user — inverting the MLPerf/SPEC-style conformance-mark
strategy (ADR-0014) in which controlling what results may wear the benchmark's name is the
project's long-term integrity lever. Keeping the name would also require actively overriding
ADR-011's own reopen rule — the kind of motivated reasoning this project exists to prevent.

Timing: nothing is published — no package, no preregistration stamp, no DOI, no filed mark,
no site deployment. This is the cheapest moment the project will ever have to fix its name;
after launch the cost compounds toward "never" (N1 switching-cost analysis, `[EI]`).

### N1 evidence summary (2026-07-21; research, NOT legal clearance)

N1 generated 55 candidates across five semantic fields, filtered on meaning / memorability /
pronunciation / spelling / international readings, then collision-screened the survivors
(PyPI/npm/crates.io JSON endpoints, GitHub users API, Homebrew, RDAP for .com/.dev, DNS NS
delegation for .io, Justia trademark web search). Finalists:

| Rank | Name | Screen result | Why it lost / won |
|---|---|---|---|
| #1 | **Irrevon** | Clear on **every** axis: PyPI/npm/crates/GitHub 404; irrevon.com/.dev RDAP-404; irrevon.io no NS; no company/product/mark surfaced | Won on clearance + legal strength (fanciful mark, the strongest category — exactly what the ADR-0014 conformance strategy needs). Accepted weaknesses, eyes open: zero pre-loaded meaning, crowded "-on" coinage register, pharma cadence, stress ambiguity |
| #2 | Talea | PyPI/npm/crates clear; GitHub user taken; all three domains registered | Best semantics found (the split tally stick = reconciliation-by-evidence), but a crowded trade-name field incl. an Italian class-42-adjacent ICT/SAP firm (talea.it) — a real trademark question |
| #3 | Estop | Registries clear; estop.com registered | "E-stop" irreversibly means *emergency stop* to robotics/safety audiences — a standing mis-description of an engine that is not a kill switch |
| reserve | Peractum | Cleanest slate for a real Latin word | Heavy, obscure, mishearing-prone |

The incumbent failed the same screen (see Context). N1's verdict: rename pre-launch,
owner-gated. N1's honest challenge to Irrevon is **sustained, not waved away**: it is a
*clear* name, not yet a *good* one — everything must be bought with messaging.

## Decision

1. **The name is Irrevon.** Owner written directive of 2026-07-21 ("the name change has to
   reflect everywhere — the code, the docs, the repo name, everything"); the directive is the
   ratification for the master-doc amendment this rides with (AM-22, AM-16 mechanics: targeted
   product-name find-replace + hash re-pin in `scripts/master-doc.sha256`).
2. **The benchmark is `IrrevonBench`** — one word, capital I capital B, matching the
   `<Name>Bench` pattern the claims registry, preregistration, and conformance-policy skeleton
   all pattern on. N1's crisper sub-brand idea ("IrrevBench") is explicitly a separate, later
   owner decision — not invented here.
3. **Counsel-screening caveat (preserved, load-bearing):** all availability and trademark
   findings above are automated research as of 2026-07-21, labeled "appears available" —
   **none of it is legal clearance.** A professional IC 9/42 clearance search on "Irrevon" is
   required before any trademark reliance, and stays on the launch checklist. Domain purchase,
   USPTO filing, and PyPI registration remain human spend/publication acts; PyPI registration
   of `irrevon` is unblocked **pending those clearances**.
4. **Schema `$id` move:** placeholder host `detent.invalid` → `https://irrevon.dev/schemas/…`.
   `$id` is metadata (identifier, not locator), not shape — recorded here because schema files
   change only with an ADR. The host stays an explicit placeholder until the domain is
   purchased.
5. **Migrations edited in place; NO 0006 rename migration.** `detent_app` → `irrevon_app` and
   the journal table `detent_schema_migrations` → `irrevon_schema_migrations` directly in
   migrations 0001–0004. The migrations are **unreleased** — no wheel, no tag, no external
   database has ever applied them; a rename migration exists to migrate an installed base, and
   there is none. Shipping one would bake `detent_*` roles into every future database forever.
   The one real cost — developers' stale local DBs — is mitigated by `irrevon doctor`, which
   detects the pre-rename signature and hints
   `docker compose down -v && … && irrevon init`. The ADR-0022 append-only journal discipline
   governs *applied* journals, which are all disposable/recreated; editing unreleased files is
   a normal edit.
6. **Fixtures regenerated, never hand-edited:** the workbench fixture set was re-captured from
   a real engine run (seed 777) after the code rename, so provenance stays honest. The
   flagship effect id `0bb7e8d6…85f5` is expected byte-identical — identity derives from
   business stable_ids + contract fields, never the product name; any drift is
   stop-and-investigate.
7. **Append-only discipline:** prior ADR texts, review-queue history rows, task files
   (`tasks/T-1xx`), and git history keep the old name — historical record, working as
   designed. ADR-011 receives only this supersession (status line in the index; its full text
   in master doc §11 is amended solely by AM-22's product-name sweep). The GitHub repository
   rename (`PranavMishra28/detent` → `…/irrevon`) is a settings mutation, **human/coordinator
   only, after merge**; in-repo URLs already carry the new path and go live with it.

## Alternatives

- **Keep "Detent"** — fails ADR-011's own reopen trigger on recorded evidence; permanent PyPI
  mismatch against a confusable same-audience product; junior-user trademark position.
- **Talea / Estop / Peractum** — see finalists table; each lost on a concrete axis Irrevon
  clears.
- **Rename-later (post-launch)** — cost compounds (stamped preregistration, permanent PyPI
  name, citations, filed marks); rejected on the switching-cost asymmetry.
- **0006 rename migration** — rejected (no installed base; permanently pollutes future
  databases with legacy role names).
- **Two-token "Irrevon Bench"** — rejected: the conformance policy protects a single-token
  mark; `<Name>Bench` consistency is worth more than marginal readability.

## Consequences

- Easier: canonical names everywhere (`pip install irrevon` when published, `irrevon init`,
  IrrevonBench, Irrevon Workbench); a fanciful mark for the ADR-0014 conformance strategy;
  the name screen (review-queue §3 item 4) resolves to a decision instead of a standing risk.
- Harder: a coined name with zero stored meaning must be earned through messaging; every
  historical document now reads under a superseded name (mitigated: this ADR + AM-22 record
  the mapping once).
- Enforced by: `make check-all` green before and after (the rename is a naming sweep, never a
  behavior edit); the fixture drift gate + flagship-id stability check; the residual-name
  sweep (old-name occurrences allowed only in history/ADRs/review-queue/tasks/.scratch).

## Risks

- Counsel screen could surface an "Irrevon" conflict later → fall back to N1's #2 (Talea) /
  #3 (Estop) before any publication act; nothing is stamped or published under the new name
  yet, so the blast radius stays in-repo.
- Registry names are unregistered until the human act → squatting window. Mitigation: PyPI
  registration is flagged unblocked-pending-clearances in the review queue; the owner decides
  timing.
- The `-on` register grows more crowded → accepted with eyes open (decision weighs clearance
  and legal strength over beauty).

## Reopen trigger

Counsel's IC 9/42 clearance search surfaces a live "Irrevon" (or confusably similar) mark or
prior same-field user; or any registry/domain in the §3.1 matrix is taken by a same-space
product before the owner registers it. Either fires a fallback evaluation of the N1
runners-up before any publication act.

## Appendix — touchpoint inventory as executed (2026-07-21)

Nine zones, ~40 touchpoints (REBUILD-BRIEF §1.1, verified against the tree):

- **A — Python package + CLI:** `src/detent/`→`src/irrevon/` (all imports); pyproject `name`,
  `[project.scripts] irrevon`, import-linter root + contracts, wheel packages/force-include
  (`irrevon/_schemas`), description; env vars `DETENT_*`→`IRREVON_*` (DSN, REFDEST_URL,
  CONFIG, LOG_FILE, TEST_HOOKS, BENCH, CRASH_AT, SYNC_AT, SYNC_DIR, REREAD_GAP_S,
  STUCK_THRESHOLD_S, AUTO_REDISPATCH_TYPES, TEST_ADMIN_DSN) incl. all test seams;
  `detent.toml`→`irrevon.toml` (config precedence chain, init scaffold, doctor, tests, site
  copy); JSONL logger docstrings; demo kept-DB `irrevon_demo_s<seed>`; demo summary key
  `detent_leg`→`irrevon_leg` (product-named artifact field); CLI `--leg irrevon`;
  `DetentError`→`IrrevonError`; uv.lock regenerated.
- **B — DB roles + migrations (edited in place, no 0006):** `irrevon_app` in 0001/0003/0004;
  `irrevon_no_rewrite()` + `irrevon_schema_migrations` in 0002/db.py; doctor stale-DB hint
  added; integration conftest DSNs.
- **C — schemas:** `$id` → `https://irrevon.dev/schemas/…` (placeholder until domain
  purchase); `$comment` wording; examples + reference-destination declarations
  (`Irrevon reference destination`, citations host).
- **D — web/:** package `irrevon-web`; `__IRREVON_DATA_MODE__` / `VITE_IRREVON_DATA_MODE` /
  `IRREVON_VRT_CONTAINER`; index.html titles; wordmark text slot (geometry untouched);
  narration copy (stage.tsx), route copy, brand SVG title text; localStorage keys
  `irrevon.*`; codegen + schema-pins regenerated; fixtures regenerated via the real engine
  (see Decision 6); motion/density token comments reworded to the mechanism ("seated click"),
  not the old product name.
- **E — site/:** `SITE_NAME = "Irrevon"` + full copy sweep (pages, DemoTranscript, styles);
  claims registry updates (`not-published` rewritten: name decided, PyPI pending clearances,
  future-tense `uv tool install irrevon`; `demo-provenance` engine commit refreshed) +
  CLAIMS.md regenerated; package `irrevon-site`.
- **F — docs/ + root:** README, AGENTS.md, docs/ci.md (incl. `gh api …/irrevon` examples,
  live at repo rename), RFC-001/002, security-policy, execution-plan (P2 + release-gate item
  updated to "adopted; counsel clearance open"), benchmark-preregistration (DRAFT throughout;
  no FROZEN section exists — verified), Makefile comments + `IRREVON_VRT_CONTAINER`
  (target names unchanged: role-named), CI workflow header comments + lychee placeholder
  exclude (`irrevon.dev`), dependabot/gitleaks comments, `.cursor` (BUGBOT, environment name,
  deny-hook comment, contracts rule), `scripts/` (bootstrap comment, `IRREVON_REPO`).
- **G — GitHub repo rename:** NOT in this change; coordinator/owner, post-merge (settings
  mutation).
- **H — unchanged by design:** git history; prior ADR texts and review-queue history rows;
  `tasks/T-1xx` files (append-only records); `.scratch/`; engine semantics, schema shapes,
  state tables, budgets, gates; mark/icon geometry and token values.
