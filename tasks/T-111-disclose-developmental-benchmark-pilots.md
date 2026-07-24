# T-111: Disclose developmental benchmark pilots

---
id: T-111
status: done
depends_on: [T-105]
invariant: "master doc §8.1–§8.7 (benchmark credibility, no favorable measurement, and no confirmatory claim before the applicable human freezes)"
---

## Objective

Correct the scientific-integrity record so pre-freeze synthetic S-REF engineering pilots
are disclosed without representing them as live-sandbox observations, confirmatory runs, or
scientific results.

## Why

ADR-0032 records a 488-effect full-matrix attribution pilot, and the harness/CLI has executed
reference-destination smoke pilots, while current prose says no benchmark or fault observation
has occurred. The preregistration is still DRAFT, so its unfrozen status text must disclose
that design-stage exposure; the frozen master doc receives only an appended human amendment
proposal.

## Context — read these first

- `AGENTS.md`
- `docs/master-doc.md` §8 and §12
- `docs/benchmark-preregistration.md` §0, §2, §5
- `docs/benchmark.md` §3, §5–§6
- `docs/execution-plan.md` ordering rationale and gate notes
- `docs/decisions/0030-bench-harness-contracts.md`
- `docs/decisions/0032-causal-histories-and-conformance.md`
- `docs/review-queue.md` append-only policy, item 36
- `scripts/check-bench-integrity.py`

## Scope

**Allowed to write:** `tasks/T-111-disclose-developmental-benchmark-pilots.md`;
`docs/benchmark-preregistration.md`; `docs/benchmark.md`; `docs/execution-plan.md`;
append-only rows in `docs/review-queue.md`; `site/src/data/claims.ts`;
`site/src/components/Badge.astro`;
`site/src/pages/benchmark.astro`; `site/src/pages/index.astro`;
`site/src/pages/roadmap.astro`; `site/src/pages/platform.astro`;
`site/src/content/research/preregistering-a-benchmark.md`;
`site/src/content/guides/benchmark-reproduction.md`;
the mechanically generated mirrors
`site/src/content/repo-docs/benchmark-preregistration.md`,
`site/src/content/repo-docs/benchmark-guide.md`,
`site/src/content/repo-docs/execution-plan.md`,
`site/src/content/repo-docs/review-queue.md`, and `site/CLAIMS.md`;
`web/src/app/routes/index.tsx`; the narrow existing web test(s) that cover its benchmark
status copy; `tests/scripts/test_benchmark_pilot_disclosure.py`.

**Forbidden:** `docs/master-doc.md`; accepted or proposed ADR text; any FROZEN
preregistration section; benchmark fixtures, runs, results, metrics, baselines, schemas,
analysis, or runtime code; freeze registrations; claims of efficacy, novelty, pristine
preregistration, human ratification, live-sandbox evidence, or confirmatory evidence;
publication and repository settings. Anything not explicitly allowed is out of scope.

## Acceptance criteria

- [x] The DRAFT preregistration inventories the S-REF/harness smoke pilots and ADR-0032's
      488-effect full-matrix attribution pilot, and states their non-confirmatory limits.
- [x] Every changed public surface distinguishes developmental S-REF observations from the
      still-empty live-sandbox and confirmatory evidence classes.
- [x] A regression test fails if the public surfaces return to categorical “no benchmark
      run/fault trial has occurred” claims or omit the developmental-pilot disclosure.
- [x] The review queue appends, without resolving, the master-doc integration and Stage-A
      integrity ruling owed to the human.
- [x] `make bench-integrity`, the targeted regression test, `make site-check`,
      `make site-test`, `make web-check`, `make web-test`, `make web-e2e`, and
      `make check` pass.

## Required validation

```bash
uv run pytest tests/scripts/test_benchmark_pilot_disclosure.py -p no:cacheprovider
make bench-integrity
make site-check
make site-test
make web-check
make web-test
make web-e2e
make check
```

## Documentation updates

Update only the DRAFT status/disclosure prose and its public projections; regenerate the
three repo-doc mirrors and claims table mechanically; append the unresolved human ruling
to `docs/review-queue.md`.

## Human review triggers — stop and ask if:

- Any correction would require editing the frozen master doc directly or changing a frozen
  preregistration section.
- Evidence appears of a real-provider sandbox call, a confirmatory run, a committed
  `bench/runs/` artifact, or pilot observations beyond the inventory recorded here.
- Resolving the Stage-A validity consequence requires a human scientific-integrity ruling;
  record it as open rather than choosing an outcome.

## Definition of done

All criteria are checked; validation output is recorded below; generated mirrors are in
sync; no writes occurred outside allowed scope; status is `done`.

## Completion record

Completed 2026-07-23.

- `uv run pytest tests/scripts/test_benchmark_pilot_disclosure.py -p no:cacheprovider`:
  3 passed.
- `make bench-integrity`: manifest, dev-seed, canary/split/freeze-honesty, and oracle
  isolation checks passed.
- `make site-check`: 0 errors; generated claims and all 37 rendered repository documents
  matched their sources (37 existing Astro hints).
- `make site-test`: 318 passed.
- `make web-check`: typecheck, lint, stylelint, format, codegen, fixture/font drift, and
  92 unit tests passed.
- `make web-test`: 92 unit and 80 story tests passed.
- `make web-e2e`: 133 workflow and WCAG 2.2 AA tests passed, including the benchmark
  readiness disclosure assertion.
- `make check`: all repository validation gates passed.
- `pnpm sync:docs` regenerated the benchmark preregistration, guide, and execution-plan
  mirrors; `pnpm claims:md` regenerated 54 claims. The review queue is deliberately
  `linkOnly` in `site/docs-manifest.json`, so no review-queue mirror exists or was invented.
