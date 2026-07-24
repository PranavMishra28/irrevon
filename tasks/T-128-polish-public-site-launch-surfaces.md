# T-128: Polish public site launch surfaces

---
id: T-128
status: done
depends_on: []
invariant: "master doc §6–§9 product scope, benchmark boundaries, and security claims remain truthful"
---

## Objective
Make the public site concise, externally legible, provenance-aware, and testable without
changing product scope or publishing anything.

## Why
The public launch surface must explain the implemented alpha clearly to evaluators while
preserving the benchmark, provider-qualification, and production-operation limits recorded
in the canonical project status and execution plan.

## Context — read these first
- `AGENTS.md`
- `docs/project-status.md`
- `docs/execution-plan.md`
- `site/README.md`
- `site/src/lib/claims.ts`
- `site/src/content/guides/`
- `site/tests/`

## Scope
**Allowed to write:** this task file; `site/**` except
`site/src/content/repo-docs/**`; `Makefile` site targets; new repository-local production
smoke scripts under `scripts/` and their tests under `tests/scripts/`; `README.md` only if
an exact source Workbench/onboarding correction is necessary and does not overlap another
active task.

**Forbidden:** generated repository-document mirrors; release files; core Python; repository
settings; publishing or deployment; product features or claims beyond canonical scope; any
file not explicitly allowed above.

## Acceptance criteria
- [x] Public navigation and footer expose Product/How it works, Demo, Benchmark, Docs,
      Install, Community, and GitHub without internal project-management jargon.
- [x] Ordinary marketing and guide prose is human-readable; technical claim provenance
      remains available in the claim registry/reference.
- [x] `/version.json` contains release version, full commit SHA, build time, benchmark
      harness version, schema version, and environment; production builds fail closed when
      trustworthy provenance is absent.
- [x] A non-publishing production smoke check validates the built site and rejects missing
      or placeholder provenance.
- [x] Visual checks cover widths 1440, 1024, 768, 390, and 320 in both themes, plus reduced
      motion, forced colors, and horizontal-overflow cases.
- [x] The integration guide example validates against the repository intent-contract schema.
- [x] Unmeasured five-minute claims are absent, and the privacy page distinguishes hosting
      request data from telemetry scrubbing.
- [x] Benchmark, provider, and production limitations remain explicit.
- [x] Focused site checks and tests pass.
- [x] `git diff --check` passes.

## Required validation
- `make site-check`
- `make site-build`
- relevant site static/drift/browser tests
- production-smoke script tests
- `git diff --check`

Completed validation:

- `make site-check` — passed.
- Production-provenance `make site-build` followed by `make site-production-smoke` — passed.
- `pnpm test` — 386 checks passed.
- `pnpm exec playwright test --project=shots` — 697 visual-matrix cases passed.
- Focused script tests — 5 passed; focused Ruff check passed.
- `python3 scripts/check-public-data.py --include-generated` and redacted gitleaks scan of
  `site/dist` — passed.
- `make check` and `git diff --check` — passed.

## Documentation updates
Update public site pages and guides in scope. Do not edit generated repository-document
mirrors.

## Human review triggers — stop and ask if:
- A requested correction contradicts the canonical product status or requires a new product
  requirement, release action, repository setting, or deployment.
- Trusted production provenance cannot be established without an external publishing action.

## Definition of done
All acceptance criteria are checked; required validation succeeds; no file outside the
declared scope is changed by this task; status is `done`.
