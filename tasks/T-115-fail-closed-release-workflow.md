# T-115: Make the dormant release workflow fail closed

---
id: T-115
status: done
depends_on: [T-112]
invariant: "docs/execution-plan.md public-release gate and ADR-0018: no package, release artifact, or publication step before every human gate closes"
---

## Objective
Make every manual dispatch of the dormant release workflow fail visibly until a separate,
human-authorized activation task replaces an unconditional refusal after every public-release
gate item is complete.

## Why
The existing `if: false` job is skipped, and GitHub can present a skipped workflow as green.
That is unsafe release-readiness evidence even though no publication occurs. A deliberate red
refusal preserves the human-only release boundary without activating any distribution step.

## Context — read these first
- `AGENTS.md`
- `docs/execution-plan.md` public-release gate
- `docs/decisions/0018-distribution-model.md`
- `docs/decisions/0028-apache-2-license.md`
- `docs/ci.md`
- `.github/workflows/release.yml`
- `Makefile`
- `tasks/T-112-fail-closed-benchmark-workflow.md`
- `tests/scripts/test_benchmark_workflow_contract.py`

## Scope
**Allowed to write:** `tasks/T-115-fail-closed-release-workflow.md`,
`.github/workflows/release.yml`, `Makefile`,
`tests/scripts/test_release_workflow_contract.py`, `docs/ci.md`, and the mechanically
generated `site/src/content/repo-docs/ci.md` mirror, plus `.github/actionlint.yaml` to
remove the release workflow's obsolete `if: false` exception.

**Forbidden:** package metadata, licenses, ADRs, master doc, execution plan, review queue,
credentials, environments, repository settings, release/tag/artifact creation, publication,
workflow activation, commits, pushes, and every path not listed above.

## Acceptance criteria
- [x] `uv run pytest tests/scripts/test_release_workflow_contract.py -p no:cacheprovider`
      exits 0 and proves the workflow is manual-only, least-privilege, and cannot skip its
      refusal.
- [x] The static contract proves no secret, variable, input, file, condition, write/OIDC
      permission, publication command, release command, tag command, or artifact step is active.
- [x] `.github/actionlint.yaml` contains no release-specific or constant-false exception.
- [x] The sole active command after credential-free checkout is `make release-gate`.
- [x] `make release-gate` exits nonzero with a clear public-release-gate refusal and creates no
      artifact.
- [x] `actionlint .github/workflows/release.yml` and
      `zizmor --offline --persona=pedantic .github/workflows/release.yml` exit 0.
- [x] `cd site && pnpm sync:docs && pnpm run sync:docs -- --check` exits 0.
- [x] `make check` and `git diff --check` pass.

## Required validation
```bash
uv run pytest tests/scripts/test_release_workflow_contract.py -p no:cacheprovider
make release-gate
actionlint .github/workflows/release.yml
zizmor --offline --persona=pedantic .github/workflows/release.yml
cd site && pnpm sync:docs && pnpm run sync:docs -- --check
make check
git diff --check
```

## Documentation updates
Update `docs/ci.md` and its generated site mirror to identify the deliberate-red release
skeleton, its reserved Make entrypoint, and the separate human activation boundary after every
public-release gate item.

## Human review triggers — stop and ask if:
- The change would activate a release path; consume a secret or OIDC token; change a repository
  setting/environment; create a tag, release, artifact, or package publication; or decide any
  unresolved release policy.

## Definition of done
All criteria checked; validation output recorded below; documentation mirror regenerated; no
writes outside allowed scope; status set to done.

## Completion record

Completed 2026-07-23.

- `uv run pytest tests/scripts/test_release_workflow_contract.py -p no:cacheprovider`:
  **4 passed**.
- `make release-gate`: **expected refusal**, Make exit 2 after the target's explicit `exit 1`;
  it printed the two gate messages and created no artifact.
- `actionlint .github/workflows/release.yml`: **passed** with no suppression.
- `zizmor --offline --persona=pedantic .github/workflows/release.yml`: **passed**, no
  findings.
- `cd site && pnpm sync:docs && pnpm run sync:docs -- --check`: **passed**, 37 rendered docs
  in sync (the local Node 25 runtime produced the package's expected Node-24-range warning).
- `make check`: **passed**, including workflow security, secret, integrity, generated-registry,
  and benchmark-integrity gates.
- `uv run ruff check tests/scripts/test_release_workflow_contract.py` and
  `uv run ruff format --check tests/scripts/test_release_workflow_contract.py`: **passed**.
- `git diff --check`: **passed**.
