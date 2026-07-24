# T-134: Close release supply-chain findings

---
id: T-134
status: done
depends_on: [T-130]
invariant: "master doc §9 and §12.3; preserve exact release identity, locked validation, artifact integrity, and human-only publication"
---

## Objective

Implement only the three substantiated T-130 release findings: lock release-path
Python validators, prove Twine does not mutate candidate artifacts, bind the
build checkout to the annotated tag and current main, and reject non-Node-24
release web builds.

## Scope

**Allowed to write:**

- this task file;
- `pyproject.toml`, `uv.lock`;
- `scripts/release-dry-run.sh`, `scripts/bootstrap-tools.sh`;
- `.github/workflows/release.yml`;
- `docs/release-process.md`, `docs/ci.md`, and the generated `docs/ci.md` site mirror;
- `tests/scripts/test_release_workflow_contract.py` and focused new tests;
- web/site package metadata only if the fail-closed Node 24 preflight requires it.

**Forbidden:** every other file; commits; tags; releases; publication; deploys;
provider calls; repository settings; history changes; credentials; and
sensitive-value output.

## Acceptance criteria

- [x] Twine and every release-path Python validator are exact-constrained in a
      dedicated dependency group represented in `uv.lock` and execute through
      `uv run --locked`.
- [x] The release dry run fails if Twine changes either candidate artifact.
- [x] The tagged job requires `HEAD`, the peeled annotated tag, and
      `origin/main` to identify the same commit.
- [x] Release web builds reject every Node major except 24 before pnpm/build.
- [x] PR/manual behavior remains non-publishing and privileged jobs remain
      separated from repository code.
- [x] Focused tests and the full non-publishing validation pass.

## Required validation

```text
actionlint .github/workflows/release.yml
zizmor --offline --persona=pedantic .github/workflows/release.yml
uv run --locked pytest -q tests/scripts/test_release_workflow_contract.py tests/scripts/test_dependabot_contract.py tests/scripts/test_dist_content_contract.py
IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
make public-truth
make check
git diff --check
```

## Definition of done

The four fail-closed controls are implemented within scope, documentation and
its mirror are synchronized, all required non-publishing checks pass, no
external state changes, and this task is marked done.

## Outcome

- Added the exact-constrained `release-validation` group for
  `check-jsonschema==0.37.4`, `spdx-tools==0.8.3`, and `twine==6.2.0`; regenerated
  `uv.lock`; release jobs opt into the bootstrap's locked branch and invoke
  validators through `uv run --locked`.
- The dry run hashes wheel/sdist before and after Twine, refuses any byte drift,
  then re-runs the exact archive-manifest check.
- The tag guard now requires checked-out `HEAD`, the peeled annotated tag, and
  current `origin/main` to be identical.
- The Workbench `prebuild` guard exits before Vite unless the active Node major
  is exactly 24. A Node 25 negative run failed as intended; the complete Node 24
  release dry run passed.
- PR/manual runs remain non-publishing; attestation and publication permission
  boundaries are unchanged.

Validation:

```text
PASS  IRREVON_LOCKED_RELEASE_VALIDATION=1 bash scripts/bootstrap-tools.sh
PASS  actionlint .github/workflows/release.yml
PASS  zizmor --offline --persona=pedantic .github/workflows/release.yml
PASS  uv run --locked pytest -q tests/scripts/test_release_workflow_contract.py tests/scripts/test_dependabot_contract.py tests/scripts/test_dist_content_contract.py
      24 passed
PASS  uv run --locked ruff check tests/scripts/test_release_workflow_contract.py
PASS  Node 25 negative prebuild check (refused before Vite)
PASS  Node 24: IRREVON_ALLOW_RELEASE_VERSION=1 make release-dry-run
      renderer hashes unchanged; archive manifests passed before and after;
      SPDX validation and checksums passed; nothing published
PASS  make public-truth
PASS  make check
PASS  site docs mirror drift check
PASS  git diff --check
```
