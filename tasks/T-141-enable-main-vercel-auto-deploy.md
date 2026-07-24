# T-141: Prepare main-only Vercel auto-deployment

---
id: T-141
status: blocked-human-review
depends_on: [T-140]
invariant: "public-site provenance remains exact and package/scientific publication stays human-gated"
---

## Objective

Configure the repository so the existing Git-connected Vercel project can
rebuild and publish the static marketing site from `main`, while refusing
automatic deployments from every other branch. Platform activation remains an
explicit owner action after merge.

## Why

The repository currently disables the Vercel Git integration after an earlier
root-level Python autodetection caused failed deployment statuses. The owner's
2026-07-24 directive replaces manual uploads with a main-only automatic
production-build policy; package releases, benchmark publication, and other
platforms remain separate gated workflows.

## Context — read these first

- `AGENTS.md`
- `docs/decisions/0027-site-vercel-deploy.md`
- `docs/ci.md`
- `site/README.md`
- `vercel.json`

## Scope

**Allowed to write:** this task file; `vercel.json`; `site/vercel.json`;
`scripts/vercel-build.sh`; `scripts/site-production-smoke.py`; related tests
under `tests/scripts/`; `.github/workflows/ci.yml`; `Makefile`; `README.md`;
`ASSETS.md`;
`docs/ci.md`; `docs/review-queue.md`; `docs/decisions/README.md`;
`docs/decisions/0027-site-vercel-deploy.md`; one new ADR; `site/README.md`;
`site/package.json`; `site/deployment-policy.test.mjs`;
`site/docs-manifest.json`; `site/docs/headers-spec.md`;
`site/scripts/sync-fonts.mjs`; and generated site documentation mirrors.

**Forbidden:** direct pushes to `main`; merging; deployment; Vercel project
creation; package/release publication; preview auto-deployments; repository
settings; secrets; history rewriting; benchmark freezes or provider calls.
Anything else is out of scope.

## Acceptance criteria

- [x] Root `vercel.json` defines the Astro build from `site/`, the exact static
      output directory, all response-header rules, and automatic-deployment
      eligibility for `main` only.
- [x] The Vercel build wrapper refuses non-production/non-`main` Git builds and
      a malformed or absent Git commit before running the site build.
- [x] Production smoke rejects a configuration that enables another branch,
      omits the protected-main rule, or changes the build/output contract.
- [x] Root `vercel.json` changes select the site CI slice.
- [x] Documentation and ADR history explain the main-only repository policy,
      the owner activation/read-back steps, and the independent human gates for
      PyPI, GitHub Release, benchmark, and provider publication.
- [x] `make check` and `make public-truth` pass.

## Required validation

`make check`; `make public-truth`; targeted Vercel build/config tests;
`make site-check`; production site build and `make site-production-smoke`;
`actionlint`; `git diff --check`; hosted CI/read-back after push.

## Documentation updates

Record ADR-0038, mark ADR-0027's manual-upload mechanic superseded, update the
ADR index and human queue, reconcile deploy documentation, and regenerate the
site mirrors.

## Human review triggers — stop and ask if:

- The existing Vercel project is not Git-connected to this repository or does
  not track `main` as production.
- A change would expose secrets, auto-publish a package/benchmark/provider run,
  deploy an unreviewed branch, or require bypassing the protected PR path.

## Definition of done

All repository-local criteria pass on the follow-up PR, hosted CI is green, and
the Vercel connector read-back proves the existing project and Node 24 runtime.
The task remains blocked until the owner merges the reviewed PR, confirms
Production Branch = `main`, reactivates the paused project, removes the GitHub
ruleset bypass, and verifies live provenance. No deployment or direct
default-branch write occurs in this task.

## Outcome

The existing Git-connected Vercel project was read back before implementation:
the platform uses Node 24, historical deployments carry repository Git
metadata, the project-level framework detection remains the stale `python`
value, and the project is paused. The available authenticated read-back did not
expose the Production Branch. The repository-root configuration now overrides
the framework detection with the locked Astro build and permits automatic
deployment only for `main`; it cannot reactivate the platform project or prove
that project-level branch setting.

Repository-local validation:

```text
PASS  make check
PASS  make public-truth
PASS  make site-check
PASS  make site-test — 393 browser/accessibility/security/SEO checks
PASS  production build through scripts/vercel-build.sh from both repository
      root and site/ working directories
PASS  make site-production-smoke — exact commit and canonical origin
PASS  40 focused production-smoke unit tests
PASS  actionlint .github/workflows/ci.yml
PASS  git diff --check
```

The reviewed branch was not merged or deployed. PR #21 merged while this task
was being validated, so the deployment policy moved to a focused follow-up PR
based on that exact merged tree.

Remaining owner actions:

1. Merge the follow-up through the reviewed pull-request path.
2. Remove the repository-role bypass from the default-branch ruleset.
3. Confirm Vercel Production Branch = `main` and reactivate the paused project.
4. Verify live `/version.json` identifies the intended merged commit.
