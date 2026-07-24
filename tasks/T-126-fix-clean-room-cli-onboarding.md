# T-126: Fix the clean-room CLI onboarding journey

---
id: T-126
status: done
depends_on: [T-124]
invariant: "master doc §7 persist-before-dispatch/evidence boundary and §9 least privilege; RFC-002 §12 CLI contracts"
---

## Objective

Make the generated-scaffold demo use explicit migration authority without
granting database administration to the runtime role, and make the complete CLI
help and first-run failure guidance accurate and testable.

## Why

The scaffolded runtime DSN uses the restricted `irrevon_app` role, but the demo
currently attempts database lifecycle operations through that DSN. The public
CLI reference also omits implemented commands and exposes several unexplained
or inert common options, so the clean-room path and its generated documentation
do not match the implemented surface.

## Context — read these first

- `AGENTS.md`
- `docs/master-doc.md` §§7 and 9
- `docs/rfc-002-engine-design.md` §12
- `src/irrevon/cli/`
- `tests/cli/`
- `tests/e2e/test_cli.py`
- `site/scripts/sync-cli-reference.mjs`

## Scope

**Allowed to write:** this task file; `src/irrevon/cli/**`; `tests/cli/**`;
only the relevant generated-scaffold coverage in `tests/e2e/**` or
`tests/process/**`; `site/scripts/sync-cli-reference.mjs`; and the actual
generated CLI-reference destination
`site/src/content/guides/cli-reference.md`.

**Forbidden:** README/install/marketing layout or release metadata; accepted
ADRs; `docs/master-doc.md`; schemas; migrations; publication, deployment,
repository settings, provider calls, benchmark execution, history mutation,
and every path not explicitly allowed above.

## Acceptance criteria

- [x] The demo requires an explicit `IRREVON_MIGRATION_DSN` for database
      lifecycle and migrations, while the engine and evidence queries use the
      configured non-superuser runtime DSN retargeted to the demo database.
- [x] Missing or unusable demo migration authority fails with a stable,
      credential-safe, actionable CLI envelope; demo cleanup uses the same
      privilege boundary.
- [x] Doctor's unreachable-ledger hint includes the required migration step.
- [x] Every supported top-level and nested CLI command has captured help, and
      meaningful option descriptions are present without inert common flags.
- [x] Focused CLI and generated-reference tests pass.
- [x] `make check` passes.

## Required validation

```text
uv run pytest tests/cli tests/e2e/test_cli.py -p no:cacheprovider
node site/scripts/sync-cli-reference.mjs --check
make site-check
make check
git diff --check
```

## Documentation updates

Regenerate `site/src/content/guides/cli-reference.md` from the corrected parser.

## Human review triggers — stop and ask if:

- A fix requires granting database-administration privileges to
  `irrevon_app`, changing migrations/schemas, or changing a product invariant.
- Validation requires a provider call, publication, deployment, or repository
  setting change.

## Definition of done

The clean generated-scaffold journey and privilege boundary are covered by
regressions; CLI help/reference agree; focused and repository gates pass; no
out-of-scope file is edited; and this task records the validation evidence.

## Validation evidence — 2026-07-24

- `uv run pytest tests/cli -p no:cacheprovider` — 43 passed.
- `uv run pytest tests/e2e/test_cli.py -p no:cacheprovider` — 8 passed,
  including a demo whose runtime DSN is explicitly `irrevon_app` while its
  migration DSN is the admin connection.
- `uv run pytest -m 'not integration' -p no:cacheprovider` — 495 passed,
  258 integration tests deselected.
- `uv run ruff check src/irrevon/cli tests/cli tests/e2e/test_cli.py` — passed.
- `uv run mypy src/irrevon/cli` — passed.
- `node site/scripts/sync-cli-reference.mjs --check` — all top-level and nested
  command captures match.
- `make site-check` — passed with 0 errors and the repository's 36 existing
  hints.
- `git diff --check` — passed.
- `uv run pytest tests/cli tests/e2e/test_cli.py
  tests/serve/test_live_journey.py -p no:cacheprovider` — 56 passed after the
  parent-owned live-service environment handoff.
- `make check` — passed after the concurrent T-125 public-truth reconciliation.

## Integration handoff completed

The live-service test launcher at `tests/serve/live_server.py` owns an admin DSN
and now explicitly forwards that same test-only authority as
`IRREVON_MIGRATION_DSN` to its `irrevon demo` child. The parent T-125 owner made
that minimal out-of-scope integration change; the live-service regression and
repository gate both pass.
