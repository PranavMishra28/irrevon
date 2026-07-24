# T-117: Harden init failure handling and DSN password injection

---
id: T-117
status: done
depends_on: []
invariant: "RFC-002 §2.1 ledger integrity and §12 stable CLI failure conventions"
---

## Objective

Make password injection into the configured ledger DSN syntactically safe and make
`irrevon init` fail closed on every migration failure except typed ledger unavailability.

## Why

[VF] `Config.resolved_dsn()` currently interpolates the raw password into a URI, so URI
metacharacters can corrupt the connection information. [VF] `irrevon init` currently catches
every migration exception as an expected first-run condition and exits successfully, which
can conceal migration-integrity, SQL, and programming failures. RFC-002 §2.1 and ADR-0022
require migration integrity, while RFC-002 §12 defines the existing CLI exit-code contract.

## Context — read these first

- `AGENTS.md`
- `docs/rfc-002-engine-design.md` §2 and §12
- `docs/decisions/0022-migration-runner.md`
- `src/irrevon/cli/config.py`
- `src/irrevon/cli/init_cmd.py`
- `src/irrevon/cli/__init__.py`
- `src/irrevon/errors.py`
- `src/irrevon/ledger/db.py`
- `tests/e2e/test_cli.py`

## Scope

**Allowed to write:** `tasks/T-117-harden-init-failure-and-dsn.md`,
`src/irrevon/cli/config.py`, `src/irrevon/cli/init_cmd.py`, and
`tests/cli/test_init_config.py`.

**Forbidden:** every other path; new dependencies; `.env` loading; database role,
authentication, or topology changes; migrations; schemas; provider code; new public error
codes; logging DSNs, passwords, or exception text.

## Acceptance criteria

- [x] Passwords containing URI metacharacters, whitespace, quotes, backslashes, and
  connection-option-looking text round-trip as one password through psycopg connection-info
  parsing without injecting another connection parameter.
- [x] Invalid connection information raises a sanitized existing typed error without exposing
  the environment value.
- [x] Only `StorageUnavailable` is reported as the nonfatal first-run database note with exit
  0.
- [x] Migration integrity, SQL, and programming failures exit 1 through the existing
  `unexpected` envelope in both plain and `--json` modes, with empty stdout and no underlying
  exception or credential text in output.
- [x] `make check` passes.

## Required validation

- `uv run pytest tests/cli/test_init_config.py -p no:cacheprovider`
- `make py-test`
- `make py-check`
- `make check`
- `git diff --check`

Results:

- `uv run pytest tests/cli/test_init_config.py -p no:cacheprovider` — 9 passed.
- `uv run pytest tests/e2e/test_cli.py::test_init_writes_templates_non_destructively
  -p no:cacheprovider` — 1 passed against a genuinely unreachable loopback port.
- `make py-test` — 316 passed, 254 deselected.
- `make py-check` — Ruff passed, mypy found no issues in 59 source files, and all four
  import-linter contracts were kept.
- `make check` — all validation gates passed, including integrity and secret scans.
- `git diff --check` — passed.

## Documentation updates

None; the CLI and migration contracts are unchanged.

## Human review triggers — stop and ask if:

- Correctness requires a new stable error code or changes to migration semantics.
- Correctness requires changing database credentials, roles, topology, or generated runtime
  files.

## Definition of done

All acceptance criteria are checked, all required validation passes, no secret value is
logged or rendered, no file outside the allowed scope is changed, and this task is `done`.
