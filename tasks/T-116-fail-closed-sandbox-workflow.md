# T-116: Make the dormant sandbox workflow fail closed

---
id: T-116
status: done
depends_on: [T-112]
invariant: "master doc §9, §13, and §15 M4: no live-sandbox contract claim or provider call before the human activation boundary closes"
---

## Objective
Make every manual dispatch of the dormant sandbox workflow fail visibly until a separate,
human-authorized M4 activation task replaces an unconditional refusal with the reviewed,
credentialed contract recipe.

## Why
`[DD]` The current skeleton can finish green when a Make target and placeholder secret exist
even though it performs no sandbox contract. That state could be mistaken for live-provider
evidence before Stage A, the ADR-0010/ADR-0012 decisions, terms review, and the M4 contract
recipe exist.

## Context — read these first
- `AGENTS.md`
- `docs/master-doc.md` §9, §13, and §15 M4
- `docs/execution-plan.md` P3–P5
- `docs/decisions/0010-stripe-api-version.md`
- `docs/decisions/0012-c2-sandbox.md`
- `docs/ci.md`
- `.github/workflows/sandbox.yml`
- `Makefile`
- `tasks/T-112-fail-closed-benchmark-workflow.md`
- `tasks/T-115-fail-closed-release-workflow.md`

## Scope
**Allowed to write:** `tasks/T-116-fail-closed-sandbox-workflow.md`,
`.github/workflows/sandbox.yml`, `Makefile`,
`tests/scripts/test_sandbox_workflow_contract.py`, `docs/ci.md`, and the mechanically
generated `site/src/content/repo-docs/ci.md` mirror.

**Forbidden:** provider or sandbox selection; credentials or secret names; adapter, harness,
schema, ADR, master-doc, execution-plan, or review-queue changes; repository settings or
environments; live-provider calls; workflow activation; trigger changes; publication;
commits; pushes; and every path not listed above.

## Acceptance criteria
- [x] `uv run pytest tests/scripts/test_sandbox_workflow_contract.py -p no:cacheprovider`
      exits 0 and proves the workflow is manual-only, approval-gated, least-privilege, and
      cannot skip or bypass its refusal.
- [x] The static contract proves no secret, variable, input, file, or condition can alter the
      sole active command after credential-free checkout: `make sandbox-stage-m4`.
- [x] `make sandbox-stage-m4` exits nonzero with a clear pre-M4 refusal and invokes no
      provider, harness, credential, or artifact-producing command.
- [x] `actionlint .github/workflows/sandbox.yml` and
      `zizmor --offline --persona=pedantic .github/workflows/sandbox.yml` exit 0.
- [x] `cd site && pnpm sync:docs && pnpm run sync:docs -- --check` exits 0.
- [x] `make check` and `git diff --check` pass.

## Required validation
```bash
uv run pytest tests/scripts/test_sandbox_workflow_contract.py -p no:cacheprovider
make sandbox-stage-m4
actionlint .github/workflows/sandbox.yml
zizmor --offline --persona=pedantic .github/workflows/sandbox.yml
cd site && pnpm sync:docs && pnpm run sync:docs -- --check
make check
git diff --check
```

## Documentation updates
Update `docs/ci.md` and its generated site mirror to identify the deliberate-red sandbox
skeleton, its reserved Make entrypoint, and the separate human M4 activation boundary.

## Human review triggers — stop and ask if:
- The change would select or call a provider; read or name a credential; activate the
  sandbox path; change the manual trigger; create or alter an environment; decide
  ADR-0010/ADR-0012; or claim a live sandbox contract passed.

## Definition of done
All criteria checked; validation output recorded below; documentation mirror regenerated;
no writes outside allowed scope; status set to done.

## Completion record

Completed 2026-07-23.

- `uv run pytest tests/scripts/test_sandbox_workflow_contract.py -p no:cacheprovider`:
  **3 passed**.
- `make sandbox-stage-m4`: **expected refusal**, Make exit 2 after the target's explicit
  `exit 1`; printed only the pre-M4 refusal.
- `actionlint .github/workflows/sandbox.yml`: **passed**.
- `zizmor --offline --persona=pedantic .github/workflows/sandbox.yml`: **passed**, no
  findings.
- `cd site && pnpm sync:docs && pnpm run sync:docs -- --check`: **passed**, 37 rendered
  docs in sync.
- `make check`: **passed**, including link, schema, secret, integrity, workflow-security,
  frozen-artifact, asset, third-party, and benchmark-integrity gates.
- `git diff --check`: **passed**.
- Additional cross-workflow regression:
  `uv run pytest tests/scripts/test_{benchmark,release,sandbox}_workflow_contract.py
  -p no:cacheprovider`: **10 passed**.
