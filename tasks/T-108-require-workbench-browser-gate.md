# T-108: Require the full workbench browser gate in pull-request CI

---
id: T-108
status: done
depends_on: [T-107]
invariant: "master doc §12.1 conformance mapping; ADR-0016 quality gates"
---

## Objective
Repair the stale full-workbench browser assertion and make the existing F3 Playwright
workflow-plus-accessibility suite a fail-closed required CI gate whenever the workbench
slice changes.

## Why
ADR-0016 requires Playwright E2E over built assets with axe enforced per E2E flow, while
ADR-0017 makes Make the CI parity surface. The suite exists as `make web-e2e`, but it is
not currently run by `ci.yml`; a stale assertion therefore escaped the required gate.

## Context — read these first
- `AGENTS.md`
- `docs/master-doc.md` §§6.3, 12.1–12.2
- `docs/decisions/0016-frontend-workbench-stack.md`
- `docs/decisions/0017-build-orchestration.md`
- `docs/decisions/0024-serve-read-surface.md`
- `docs/ci.md`
- `Makefile`
- `.github/workflows/ci.yml`
- `web/README.md`
- `web/playwright.config.ts`

## Scope
**Allowed to write:** `tasks/T-108-require-workbench-browser-gate.md`,
`.github/workflows/ci.yml`, `Makefile`, `docs/ci.md`,
`site/src/content/repo-docs/ci.md`, the single stale assertion under
`web/e2e/workflows/surfaces.spec.ts`, and
`tests/scripts/test_ci_web_e2e_contract.py`.

**Forbidden:** product/runtime code or copy, schemas, migrations, accepted ADRs,
`docs/master-doc.md`, benchmark artifacts or metrics, VRT baselines, dependency or
lockfile changes, test skips/retries/weakening, repository settings, releases, and
publication. Anything not listed as allowed is out of scope.

## Acceptance criteria
- [x] `make web-e2e` exits 0 with both `e2e` and `a11y` projects selected and zero
      retries/skips introduced.
- [x] `ci.yml` runs one `make web-e2e` job for every workbench-relevant change and
      `ci-required` fails if that job fails, is cancelled, or is incorrectly skipped.
- [x] A narrow contract test proves both the positive web-change requirement and the
      non-web legitimate-skip path from the workflow text.
- [x] `make check` passes.
- [x] `actionlint .github/workflows/ci.yml` and
      `zizmor --persona=pedantic --offline .github/workflows/ci.yml` pass.

## Required validation
```sh
uv run pytest tests/scripts/test_ci_web_e2e_contract.py -p no:cacheprovider
make web-e2e
make check
actionlint .github/workflows/ci.yml
zizmor --persona=pedantic --offline .github/workflows/ci.yml
```

Attach exact results below on completion.

## Documentation updates
Update `docs/ci.md` and regenerate its mechanically mirrored site copy so the tier map,
local parity, and conditional-gate account match the workflow.

## Human review triggers — stop and ask if:
- The suite failure requires changing product behavior, copy, a visual baseline, a
  dependency, or an accepted decision rather than correcting an obsolete assertion.
- Making F3 required would require a repository-setting change or a new external service.

## Definition of done
All criteria checked; validation output attached; documentation mirror regenerated; no
writes outside allowed scope; status set to `done`.

## Completion record — 2026-07-23

- `uv run pytest tests/scripts/test_ci_web_e2e_contract.py -p no:cacheprovider`:
  **3 passed in 0.15s**.
- `make web-e2e` under the repository-pinned Node 24 runtime: **133 passed in
  26.3s**, both `e2e` and `a11y`; no skips or retries.
- `make check`: **all validation gates passed**.
- `make py-check`: Ruff, mypy (**59 source files**), and all four import contracts
  passed, covering the new Python contract test on the same backend-static path CI
  will select for a `tests/` change.
- `actionlint .github/workflows/ci.yml`: exit 0, no findings.
- `zizmor --persona=pedantic --offline .github/workflows/ci.yml`: **No findings
  to report**.
- `pnpm --dir site sync:docs -- --check`: **37 rendered docs match their
  repository sources**.
- `git diff --check`: exit 0.
