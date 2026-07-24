# T-119: Pin CI Node and fix Attention reflow

---
id: T-119
status: done
depends_on: [T-108]
invariant: "master doc §12.1 conformance mapping; ADR-0016 quality gates"
---

## Objective
Make every active Node-bearing CI job use the repository-declared Node 24 runtime and
remove the Linux-only 320px Attention-page overflow that the required F3 gate exposed.

## Why
The hosted runner used Node 22 even though both frontend packages require Node 24, so CI
was not exercising the declared toolchain. After reproducing the failing route in the
pinned Linux Playwright container under Node 24, the remaining failure was traced to an
unbreakable destination work-item key in the Attention list.

## Context — read these first
- `AGENTS.md`
- `docs/master-doc.md` §§12.1–12.2
- `docs/decisions/0016-frontend-workbench-stack.md`
- `docs/decisions/0017-build-orchestration.md`
- `docs/ci.md`
- `.github/workflows/ci.yml`
- `.github/workflows/nightly.yml`
- `web/.nvmrc`
- `site/.nvmrc`
- `web/src/features/attention/worklist.tsx`
- `web/e2e/workflows/responsive.spec.ts`

## Scope
**Allowed to write:** `tasks/T-119-pin-ci-node-and-fix-attention-reflow.md`,
`.github/workflows/ci.yml`, `.github/workflows/nightly.yml`, `docs/ci.md`,
`site/src/content/repo-docs/ci.md`, `web/src/features/attention/worklist.tsx`, and
`tests/scripts/test_ci_node_runtime_contract.py`.

**Forbidden:** schemas, migrations, accepted ADRs, `docs/master-doc.md`, package or
lockfile changes, VRT baselines, test skips/retries/weakening, repository settings,
releases, deployments, and publication. Anything not listed as allowed is out of scope.

## Acceptance criteria
- [x] Every active CI/nightly job that invokes Corepack first installs the appropriate
      repository-declared Node runtime through the SHA-pinned `actions/setup-node` action.
- [x] The 320px Attention route has no body-level horizontal overflow in the pinned Linux
      Playwright container; the destination-key evidence remains fully visible and usable.
- [x] The full zero-retry `make web-e2e` suite passes.
- [x] The workflow contract test, `make check`, actionlint, and offline pedantic zizmor pass.

## Required validation
```sh
uv run pytest tests/scripts/test_ci_node_runtime_contract.py -p no:cacheprovider
docker run --rm --ipc=host -e CI=1 -v "$PWD":/work -w /work/web \
  mcr.microsoft.com/playwright:v1.61.1-noble \
  bash -lc 'corepack enable && pnpm install --frozen-lockfile --store-dir /tmp/pnpm-store && pnpm exec playwright test e2e/workflows/responsive.spec.ts --project=e2e --workers=1'
make web-e2e
make check
actionlint .github/workflows/ci.yml .github/workflows/nightly.yml
zizmor --offline --persona=pedantic .github/workflows/
```

## Documentation updates
Document the SHA-pinned Node-runtime setup in `docs/ci.md` and regenerate its site mirror.

## Human review triggers — stop and ask if:
- The reflow repair would require changing product meaning, hiding evidence, altering a
  visual baseline, weakening the browser gate, or changing a dependency.
- The workflow repair would require a repository-setting change or a new external service.

## Definition of done
All criteria checked; validation output attached; documentation mirror regenerated; no
writes outside allowed scope; status set to `done`.

## Completion record — 2026-07-23

- `uv run pytest tests/scripts/test_ci_node_runtime_contract.py
  tests/scripts/test_ci_web_e2e_contract.py -p no:cacheprovider`: **5 passed in 0.16s**.
- Pinned Linux Playwright container, Node 24, one worker:
  `responsive.spec.ts` **9 passed in 36.9s**, including the formerly failing
  `/attention` route at 320px.
- Node 24 `make web-e2e`: **133 passed in 28.1s**, zero retries or skips.
- Node 24 `make web-check`: typecheck, ESLint, Stylelint, formatting, generated-source
  drift, fixture/font drift, and **92 unit tests** passed.
- `make check`: all validation gates passed; gitleaks found no leaks; master-doc,
  schema, asset, notice, benchmark, frozen-artifact, link, and workflow gates were green.
- `make py-check`: Ruff, mypy (**59 source files**), and all four import contracts passed.
- Node 24 `make site-check`: **0 errors / 0 warnings**; all generated registries and the
  37-document mirror were in sync (37 existing Astro hints remain non-blocking).
- `actionlint .github/workflows/ci.yml .github/workflows/nightly.yml`: exit 0.
- `zizmor --offline --persona=pedantic .github/workflows/`: **No findings to report**.
- `git diff --check`: exit 0.
