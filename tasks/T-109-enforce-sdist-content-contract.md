# T-109: Enforce the source-distribution content contract

---
id: T-109
status: done
depends_on: [T-106]
invariant: "ADR-0018: one Python distribution contains the engine contracts and prebuilt workbench, and every install path remains Node-free"
---

## Objective

Restrict the sdist to its declared build and runtime inputs and fail closed when either
Python artifact contains an unexpected top-level path.

## Why

ADR-0018 requires one independently installable Python distribution, not a snapshot of the
repository. Hatch's unanchored sdist include patterns currently admit unrelated repository
trees with matching descendants, leaking docs, site/web sources, tests, tasks, and benchmark
working data into the artifact.

## Context — read these first

- `docs/decisions/0018-distribution-model.md`
- `docs/decisions/0024-serve-read-surface.md`
- `pyproject.toml`
- `hatch_build.py`
- `Makefile` (`dist`, `dist-smoke`)
- `scripts/dist-smoke.sh`

## Scope

**Allowed to write:** `tasks/T-109-enforce-sdist-content-contract.md`, `pyproject.toml`,
`scripts/dist-smoke.sh`, `scripts/check-dist-contents.py`, and
`tests/scripts/test_dist_content_contract.py`.

**Follow-up integration-correction scope:** `tests/bench/test_contamination.py` may also be
updated solely to make its pre-existing packaging-contamination assertion enforce the
ratified `only-include` contract above. The task file itself may record this correction.

**Forbidden:** license policy or third-party notice contents; package metadata authorship;
release workflows; dependencies; product runtime; schemas or migrations; benchmark data or
controls; `docs/master-doc.md`; accepted ADRs; generated workbench assets; publication.
Anything not listed as allowed is out of scope.

## Acceptance criteria

- [x] `make dist` exits 0 and the sdist contains exactly the declared top-level allowlist:
      Python source, schemas, migrations, canonical README/licensing/build inputs (including
      Hatch's forced VCS-exclusion input), and generated package metadata.
- [x] The sdist contains `src/irrevon/_web/index.html`; the wheel contains the corresponding
      embedded workbench plus schemas and migrations.
- [x] Given a synthetic sdist with any extra top-level path (including `docs/`, `site/`,
      `web/`, `tests/`, `tasks/`, or `bench/`), the artifact checker exits non-zero and names
      the unexpected path.
- [x] `make dist-smoke` installs both the wheel and sdist in the Node-less smoke container.
- [x] `make check` passes.

## Required validation

```sh
uv run pytest tests/scripts/test_dist_content_contract.py -p no:cacheprovider
make dist
uv run python scripts/check-dist-contents.py dist/irrevon-*.tar.gz dist/irrevon-*.whl
make dist-smoke
uvx twine check dist/*
make check
```

## Documentation updates

None; the executable contract and adjacent packaging comments are the source for artifact
contents.

## Human review triggers — stop and ask if:

- The Node-free sdist build requires shipping any new repository surface or dependency.
- Required legal metadata cannot be preserved without changing license policy or contents.
- The fix requires changing the single-distribution or embedded-workbench decisions.

## Definition of done

All criteria checked; validation output attached; no writes outside allowed scope; status
set to `done`.

## Completion record — 2026-07-23

- `uv run pytest tests/scripts/test_dist_content_contract.py -p no:cacheprovider` — 7 passed,
  including one acceptance case and rejection of each forbidden repository tree.
- `make dist` — built the sdist and wheel; the sdist checker reported only `.gitignore`,
  `LICENSE`, `LICENSING.md`, `NOTICE`, `PKG-INFO`, `README.md`, `hatch_build.py`,
  `migrations`, `pyproject.toml`, `schemas`, and `src` at the archive root.
- `uv run python scripts/check-dist-contents.py dist/irrevon-*.tar.gz
  dist/irrevon-*.whl` — both artifact contracts passed, including the staged workbench,
  schemas, migrations, legal files, and stale-package guard.
- `make dist-smoke` — wheel and sdist installed and completed the full journey in the
  Node-less Python 3.13 container.
- `uvx twine check dist/*` — both artifacts passed.
- `uvx check-wheel-contents dist/irrevon-*.whl` — wheel passed.
- `make check` — all repository validation gates passed.

## Follow-up integration correction — 2026-07-23

The full Python suite exposed one stale assertion in
`tests/bench/test_contamination.py`: it still read Hatch's removed, pattern-based `include`
key. The assertion now checks the exact project-root `only-include` inputs that produce the
sdist allowlist, rejects a simultaneous legacy `include` key, and retains the direct
benchmark-data exclusion checks. No production or benchmark data changed.
