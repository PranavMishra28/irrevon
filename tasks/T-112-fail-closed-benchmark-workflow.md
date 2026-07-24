# T-112: Make the dormant benchmark workflow fail closed

---
id: T-112
status: done
depends_on: [T-105]
invariant: "master doc §8.5 and §12.5: no confirmatory execution or benchmark claim before the human freeze and registered run procedure"
---

## Objective
Make the manual benchmark workflow incapable of finishing green until a later,
human-authorized Stage-B activation task replaces an unconditional refusal with the real
registered benchmark recipe.

## Why
The M7 skeleton currently succeeds when `pyproject.toml` and a placeholder environment
secret exist, even though it executes no benchmark. That green state could be mistaken for
scientific evidence and contradicts the preregistration §0 freeze boundary.

## Context — read these first
- `AGENTS.md`
- `docs/master-doc.md` §8, §12.2, §12.5, §13, §15 M7
- `docs/benchmark-preregistration.md` §0
- `docs/benchmark.md` status and §7
- `bench/README.md`
- `docs/execution-plan.md` P7 and public-release gate
- `docs/ci.md`
- `.github/workflows/benchmark.yml`
- `Makefile`
- `tests/scripts/test_ci_web_e2e_contract.py`

## Scope
**Allowed to write:** `tasks/T-112-fail-closed-benchmark-workflow.md`,
`.github/workflows/benchmark.yml`, `Makefile`,
`tests/scripts/test_benchmark_workflow_contract.py`, `docs/ci.md`, and the mechanically
generated `site/src/content/repo-docs/ci.md` mirror.

**Forbidden:** benchmark registrations, results, fixtures, metrics, schemas, harness or
provider runtime; master doc, preregistration, ADRs, review queue; credentials,
environments, repository settings, workflow triggers other than preserving manual dispatch,
live-provider calls, activation, publication, commits, and pushes.

## Acceptance criteria
- [x] `uv run pytest tests/scripts/test_benchmark_workflow_contract.py -p no:cacheprovider`
      exits 0 and proves the workflow is manual-only, approval-gated, least-privilege, and
      executes exactly the reserved Stage-B Make entrypoint.
- [x] The static contract proves neither a configured secret nor a file-existence condition
      can bypass the refusal, and proves the refusal target contains no benchmark/provider
      execution command.
- [x] `make benchmark-stage-b` exits nonzero with a clear pre-Stage-B refusal and does not
      read credentials or create artifacts.
- [x] `actionlint .github/workflows/benchmark.yml` and
      `zizmor --offline --persona=pedantic .github/workflows/benchmark.yml` exit 0.
- [x] `cd site && pnpm sync:docs && pnpm run sync:docs -- --check` exits 0.
- [x] `make check` passes.

## Required validation
```bash
uv run pytest tests/scripts/test_benchmark_workflow_contract.py -p no:cacheprovider
make benchmark-stage-b
actionlint .github/workflows/benchmark.yml
zizmor --offline --persona=pedantic .github/workflows/benchmark.yml
cd site && pnpm sync:docs && pnpm run sync:docs -- --check
make check
```

## Documentation updates
Update `docs/ci.md` and its generated site mirror to state that the workflow is deliberately
red, identify the reserved Make entrypoint, and list the human Stage-B activation boundary.

## Human review triggers — stop and ask if:
- The change would perform or enable a benchmark run, create/fill a freeze registration,
  consume a credential, alter the `benchmark` environment, or change the trigger.
- A real Stage-B execution recipe or provider behavior must be selected.

## Definition of done
All criteria checked; validation output recorded below; documentation mirror regenerated;
no writes outside allowed scope; status set to done.

## Completion record

Completed 2026-07-23.

- `uv run pytest tests/scripts/test_benchmark_workflow_contract.py -p no:cacheprovider`:
  **3 passed**.
- `make benchmark-stage-b`: **expected refusal**, Make exit 2 after the target's explicit
  `exit 1`; printed only the Stage-B refusal and created no output.
- `actionlint .github/workflows/benchmark.yml`: **passed**.
- `zizmor --offline --persona=pedantic .github/workflows/benchmark.yml`: **passed**, no
  findings.
- `cd site && pnpm sync:docs && pnpm run sync:docs -- --check`: **passed**, 37 rendered
  docs in sync.
- `make check`: **passed**, including workflow security, secret, freeze, generated-registry,
  and benchmark-integrity gates.
- Additional requested validation `make py-test` reached **293 passed / 1 failed / 254
  deselected**. The unrelated pre-existing failure is
  `tests/bench/test_contamination.py::test_packaging_excludes_benchmark_data`: it expects
  `tool.hatch.build.targets.sdist.include`, while the committed distribution contract now
  uses `only-include`. Neither file is in this task's allowed scope; T-112's test passes
  within that full run.
