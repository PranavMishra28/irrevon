# T-127: Prepare release and dependency contracts for v0.1.0

---
id: T-127
status: done
depends_on: [T-124]
invariant: "master doc §12.3 and §13; preserve independent release review, truthful unpublished status, and human-only publication gates"
---

## Objective

Prepare the non-publishing `0.1.0` Alpha package, release workflow, and
Dependabot contracts while keeping every external release and privacy blocker
explicit.

## Why

The public source is ready for a release-candidate review, but its package
metadata remains a development version, the tag guard accepts stale main
commits, PyPI README rendering is not gated, and routine dependency updates
still produce one pull request per ecosystem.

## Context — read these first

- `AGENTS.md`
- `docs/master-doc.md` §12.3 and §13
- `docs/decisions/0018-distribution-model.md`
- `docs/execution-plan.md`
- `docs/release-process.md`
- `.github/workflows/release.yml`
- `.github/dependabot.yml`

## Scope

**Allowed to write:** this task file; `.github/dependabot.yml`;
`.github/workflows/release.yml`; `pyproject.toml`; `src/irrevon/__init__.py`;
`PACKAGE_README.md`; `CHANGELOG.md`; `CITATION.cff`;
`docs/release-process.md`; `docs/ci.md` and its generated site mirror;
`scripts/release-dry-run.sh`; `scripts/launch-audit.sh`; and focused
repository-local release/Dependabot tests.

**Forbidden:** every other path; README and site product/install/layout/status
surfaces; publishing, tagging, deployment, repository settings, history
rewrites, sensitive historical values, provider calls, scientific freezes or
results, and claims that an external owner gate has closed.

## Acceptance criteria

- [x] Package metadata consistently prepares `0.1.0` with the Alpha classifier,
      live site/docs URLs, final changelog/citation data, and no claim that the
      package has been published.
- [x] The release dry run validates strict PyPI README rendering through an
      exact-version-pinned tool and remains non-publishing on pull requests and
      manual dispatches.
- [x] Tagged publication requires an owner-pushed annotated `v0.1.0` tag whose
      peeled commit exactly equals the reviewed current `origin/main`.
- [x] Dependabot defines one monthly multi-ecosystem routine group, per-ecosystem
      security groups, no routine frontend/site majors, no automerge, explicit
      labels and owner assignment, and a documented quarterly major process.
- [x] Edge case: stale-main tags and non-development dry-run execution fail
      unless the explicit release-candidate validation flag is present.
- [x] `make check` passes.

## Required validation

```text
actionlint .github/workflows/release.yml
uv run pytest -q tests/scripts/test_release_workflow_contract.py tests/scripts/test_dependabot_contract.py
IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
node site/scripts/sync-docs.mjs --check
make check
git diff --check
```

## Documentation updates

Update the release process, CI dependency policy, and generated CI mirror
without changing published-state or owner-blocker truth.

## Human review triggers — stop and ask if

- Publication, tagging, settings changes, history rewriting, or closure of a
  master-doc §13 or historical-privacy blocker becomes necessary.
- The pinned README renderer cannot be locked without widening scope.

## Definition of done

All criteria are checked, focused validations pass, generated CI documentation
has no drift, no file outside scope changes from this task, and the task records
completion evidence without committing or performing an external action.

## Completion evidence — 2026-07-24

- `actionlint .github/workflows/release.yml` and shell syntax checks passed.
- Ten focused release/Dependabot contract tests passed.
- `IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run` built the exact
  `irrevon-0.1.0` wheel and sdist; archive-content, Twine 6.2.0
  `check --strict`, SPDX, and checksum gates passed without publication.
- Direct archive inspection confirmed `0.1.0`, the Alpha classifier, live
  homepage/docs metadata, the packaged README, and the intentional absence of
  a citation release date.
- Dependabot YAML parsed with five ecosystems assigned to one monthly group;
  repository-local contracts cover per-ecosystem security groups, ignored
  routine web/site majors, labels, assignment, and absence of automerge.
- `node site/scripts/sync-docs.mjs --check`, `make check`, and
  `git diff --check` passed on the integrated launch worktree.

No tag, release, upload, deployment, repository setting, history, provider, or
scientific state was changed. Publication and historical-privacy decisions
remain explicitly human-only.
